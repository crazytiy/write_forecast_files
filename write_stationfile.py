'''
    利用已经生成的强对流格点预报数据，生成站点文件
    运行流程：
        1. 根据文件名读取已经生成的强对流格点预报数据
        2. 根据station_filename读取站点信息(默认./userdata/stations98.csv)
        3. 根据站点经纬度坐标，将格点插值到站点，生成站点预报
        4. 按照格式将数据写入txt文件
    
'''

import os
from datetime import datetime
import datetime as dt
import pandas as pd
import numpy as np
import pygrib
from scipy.interpolate import griddata
from glob import glob

regions={
    'HNCS':'长沙市',
    'HNZZ':'株洲市',
    'HNXT':'湘潭市',
    'HNUY':'岳阳市',
    'HNCD':'常德市',
    'HNZJ':'张家界市',
    'HNXX':'湘西土家族苗族自治州',
    'HNHH':'怀化市',
    'HNYY':'益阳市',
    'HNSY':'邵阳市',
    'HNLD':'娄底市',
    'HNYZ':'永州市',
    'HNHY':'衡阳市',
    'HNCZ':'郴州市',
    'HNXZ':'信息中心',
    'HNFW':'气象服务中心',
    'HNKY':'科研所',
    'HNFY':'湖南分院',
    'CCCC':'测试'
    }

# 定义函数read_stadata_from_grib，用于从grib文件中读取数据，并插值到指定的经纬度
def read_stadata_from_grib(filename,slat,slon):
    '''
    从grib文件中读取数据，并插值到指定的经纬度
        参数：
            filename: grib文件路径
            slat: 纬度列表
            slon: 经度列表
        返回值：
            stadatas: 插值后的列数据
    '''
    # 打开grib文件
    pg=pygrib.open(filename)
    # 选择所有数据
    pg=pg.select()
    # 创建空列表，用于存放插值后的数据
    stadatas=[]
    # 遍历所有数据
    for i in range(len(pg)):
        # 获取数据，纬度，经度
        data,lats,lons=pg[i].data()
        # 对数据进行插值
        stadata= griddata((lons.flatten(), lats.flatten()), data.flatten(), (slon, slat),method='nearest')
        # 将插值后的数据添加到列表中
        stadatas.append(stadata)
    # 将列表转换为numpy数组
    stadatas=np.stack(stadatas,axis=0)
    stadatas=np.where(stadatas>0,1,0)   #大于0为1，小于0为0；grib格式中，RAT：63 强降水；-1无，SMG：61 雷暴大风、-1无。转换成：1 有、0 无
    # 返回插值后的数据
    return stadatas

# 定义函数stationinfo，用于读取stationinfo文件，并返回台站号、纬度和经度
def read_stationinfo(filename,select_city=None):
    '''
    读取stationinfo文件，并返回台站号、纬度和经度
        参数：
            filename: stationinfo文件路径
            select_city: 选择的城市，如'长沙市'
        返回值：
                ids: 台站号列表
                lats: 纬度列表
                lons: 经度列表
    '''

    # 读取文件
    stations=pd.read_csv(filename,encoding='gbk')
    # 筛选出湘潭市的信息
    if select_city=='测试':select_city=None
    if select_city is not None:
        if select_city in ['信息中心','气象服务中心','科研所','湖南分院']:
            stations=stations.loc[stations['市'].isin(['长沙市','株洲市','湘潭市'])]
            # 重置索引
            stations.reset_index(drop=True,inplace=True)
        else:
            stations=stations.loc[stations['市']==select_city]
            stations.reset_index(drop=True,inplace=True)

    # 获取台站号、纬度和经度
    ids=stations['台站号'].values
    lats=stations['纬度'].values.astype('float')
    lons=stations['经度'].values.astype('float')
    # 返回结果
    return ids,lats,lons
        
def write_station(ratfile,smgfile,save_path,region,city=None,station_filename='./userdata/stations98.csv'):
    '''
    根据已经生成的强对流格点预报数据，生成站点文件
        参数：
            ratfile: 短强格点预报路径
            smgfile: 雷暴大风格点预报路径
            save_path: 站点预报文件保存路径
            region: 区域，如'CCCC'
            city: 城市，如'长沙市'
            station_filename: 站点信息文件路径，默认'./userdata/stations98.csv'
    '''
    assert region in regions.keys() ,'region参数错误，请重新输入'
    if city is None:city=regions[region]
    nowtime=datetime.now()
    nowtime=nowtime.strftime('%Y%m%d%H%M%S')
    #创建一个文本文件并写入
    date=datetime.now()
    hour=date.hour
    if hour<9:hour=0
    else:hour=12
    date=date-dt.timedelta(hours=8)
    ids,lats,lons=read_stationinfo(station_filename,select_city=city)
    ratdata=read_stadata_from_grib(ratfile,lats,lons)
    smgdata=read_stadata_from_grib(smgfile,lats,lons)
    date_str = date.strftime('%Y%m%d')+str(hour).zfill(2)+'00'
    date=datetime.strptime(date_str,'%Y%m%d%H%M')

    # 创建文件名，注意文件名时间为北京时，文件内大部分是世界时
    filename=f'Z_NWGD_C_{region}_{nowtime}_P_OGFP-SPFC-STA-{(date+dt.timedelta(hours=8)).strftime("%Y%m%d%H%M")}-02401.txt'
    # 连接输出路径和文件名
    filename = os.path.join(save_path, filename)
    
    if region not in ['HNXZ','HNFW','HNKY','HNFY','CCCC','HNXX']:
        str_city=city[:-1]
    elif region=='HNXX':
        str_city='湘西州'
    else:
        str_city=city

    with open(filename, 'w') as f:
        f.write('ZCZC\n')
        f.write(f'FSCI50 {region} {(date+dt.timedelta(hours=8)).strftime("%d%H%M")}\n')
        f.write(f'{date.strftime("%Y%m%d%H")}时{str_city}网格竞赛强对流预报产品\n')
        f.write(f'SPCC     {date.strftime("%Y%m%d%H")}\n')
        f.write(f'{len(ids)}\n')
        for i in range(len(ids)):
            # 示例 57679 113.1972 28.2117 115 24 23
            f.write(f'{ids[i]} {lons[i]} {lats[i]} 100 24 23\n')
            for j in range(12):
                strs=f'{j+1} '
                for k in range(21):
                    strs+=f'999.9 '
                f.write(strs+f'{ratdata[j,i]} {smgdata[j,i]}\n')
            for j in range(12):
                strs=f'{j+13} '
                for k in range(23):
                    strs+=f'999.9 '
                f.write(strs+'\n')
        f.write('NNNN\n')
    print(f'{filename} 站点文件写入完成')

if __name__ == '__main__':
    #设置对流格点预报路径和保存路径（自己生成的格点预报）！！！！！
    source_path='./output'
    ratfile=glob(os.path.join(source_path,'*-RAT_*.GRB2'))[0] # 修改短强格点预报路径！！！！！
    smgfile=glob(os.path.join(source_path,'*-SMG_*.GRB2'))[0] # 修改雷暴大风格点预报路径！！！！！
    save_path = './output'
    # 写入强对流数据
    # 修改region为本地区域表示！！！！！
    write_station(ratfile,smgfile,save_path,region='CCCC')
