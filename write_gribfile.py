'''
    利用本地数据修改grib并保存
    使用条件：
    1.data:本地区域的数据的numpy数组（空间分辨率0.01°），二维（单预报时次）或三维（多预报时次）
    2.extent:本地区域经纬度范围，需要与data完全对应,格式为(min_lat, max_lat, min_lon, max_lon)
    使用方法:
    修改"if __name__ == '__main__':"下面的部分，按示例修改参数，然后运行即可。
'''
import os
import pygrib
import xarray as xr
import numpy as np
import datetime as dt
from datetime import datetime
from glob import glob

NUM={"RAT":63,"SMG":61}

def create_da(data, extent, step=0.01, round_decimal=2):
    """
    根据给定的数据、范围和步长创建一个xarray.DataArray对象。

    参数：
    data (numpy.ndarray ):输入数据，numpy数组。
    extent (tuple):数据的经纬度范围，格式为(min_lat, max_lat, min_lon, max_lon)。
    step (float, optional):经纬度网格的步长，默认为0.01。
    round_decimal (int, optional):经纬度网格的小数位数，默认为2。

    返回：
    xarray.DataArray:具有指定维度、坐标和数据的DataArray对象。
    """
    assert data.ndim <= 3 and data.ndim > 1  # Check if the dimension is less than or equal to 3 and greater than 1
    lat_grid = np.round(np.arange(extent[0], extent[1] + step / 10., step), round_decimal)
    lon_grid = np.round(np.arange(extent[2], extent[3] + step / 10., step), round_decimal)
    if data.ndim == 2:
        dims = ('lat', 'lon')
        coords = {'lat': lat_grid, 'lon': lon_grid}
    else:
        dims = ('ftime', 'lat', 'lon')
        coords = {'ftime': np.arange(1, data.shape[0]+1), 'lat': lat_grid, 'lon': lon_grid}
    data = xr.DataArray(data, dims=dims, coords=coords)
    return data


#起报时间（YYYYmmddHHMM），每小时温度值（24*576*576），模板文件，输出文件
def _write_grib(sdate,data_array,varname,extent,gribfile,OutFile,
               check_name=None,ftimes=None,step=0.01,round_decimal=2):    
    """
    将给定的数据数组替换为指定的预报场数据，并将结果写入新的GRIB文件。
    参数：
        sdate (str): 起报时间，格式为'YYYYMMDDHHMM'。
        data_array (xr.DataArray): 需要替换的数据数组。
        gribfile (str): 原始GRIB文件路径。
        OutFile (str): 输出GRIB文件路径。
        check_name (str, 可选): 检查原始GRIB文件中的数据名称是否与给定名称相同。默认为None。
        ftimes(None or list(int)):给定自定义的预报时次标签列表，默认自动生成（间隔为1）
    返回：
    无。新文件将被写入到指定的OutFile路径。
    """
    
    # assert isinstance(data_array,xr.DataArray) #判断是否为DataArray
    if isinstance(sdate,int):
        print('warning:sdate为整型，建议用str类型更安全')
        sdate=str(sdate)
    sdate=datetime.strptime(sdate,'%Y%m%d%H%M')
    #numpy数组转DataArray
    data_array=create_da(data_array,extent,step,round_decimal) 
    lat_grid=data_array.lat.values 
    lon_grid=data_array.lon.values
    source_data=data_array.values
    # 读取原始grib文件  
    try:
        grbs = pygrib.open(gribfile )
    except Exception as e:
        print('Error opening GRIB file:', gribfile)
        print(e)
        return
    data0=grbs.select()[0]
    if check_name is not None:
        assert data0.name==check_name
    # 获取原始文件经纬度数组
    target_lat_grid=np.round(data0.latlons()[0][:,0],2)
    target_lon_grid=np.round(data0.latlons()[1][0,:],2)     
    # 新建一个grib文件，将修改后的数据写入
    grbout = open(OutFile,'wb')
    if source_data.ndim<=2:source_data=source_data[np.newaxis,...]
    if ftimes is None:
        if varname == 'TMP':sp=1
        else:sp=0
        ftimes=np.arange(sp,source_data.shape[0]+1)
    for i in range(source_data.shape[0]):  
        try:
            values=source_data[i]  #替换原始文件中的温度数据
            if source_data.shape[0]==1: #若为单时次文件则直接获取其第一个msg数据
                sel_tmp=grbs.select()[0]
            else: # 多预报时次则根据时次来检索对应msg
                sel_tmp=grbs.select(forecastTime=ftimes[i])[0]
            expanded_values = sel_tmp.values

            # 替换grib对应区域数据
            x = expanded_values[(target_lat_grid >= lat_grid.min()) & (target_lat_grid <= lat_grid.max())]  # 第一步
            x[:, (target_lon_grid >= lon_grid.min()) & (target_lon_grid <= lon_grid.max())] = values  # 第二步
            expanded_values[(target_lat_grid>= lat_grid.min())& (target_lat_grid<=lat_grid.max())] = x  # 第三步
            if varname in ['RAT','SMG']:
                expanded_values=np.where(expanded_values<=0,-1,NUM[varname])
            sel_tmp.values= expanded_values  #替换原始文件中的温度数据(省台修改，原为source_data[i])
           
            #修改起报日期、时间      
            sel_tmp.dataDate = int(sdate.strftime('%Y%m%d'))
            sel_tmp.dataTime = int(sdate.strftime('%H%M')) #固定格式到分钟
            if varname in ['TMAX','TMIN']:
                sel_tmp.yearOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(days=1)).year)
                sel_tmp.monthOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(days=1)).month)
                sel_tmp.dayOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(days=1)).day)
                sel_tmp.hourOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(days=1)).hour)
            else:
                sel_tmp.yearOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(hours=i+1)).year)
                sel_tmp.monthOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(hours=i+1)).month)
                sel_tmp.dayOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(hours=i+1)).day)
                sel_tmp.hourOfEndOfOverallTimeInterval = int((sdate+dt.timedelta(hours=i+1)).hour)

            # 写入新文件
            msg = sel_tmp.tostring()
            grbout.write(msg)
        except Exception as e:
            print('---文件写入失败.')
            print(e)
            grbs.close()
            grbout.close()
            return
    grbs.close()
    grbout.close()
    print('---文件生成成功：',OutFile)

def name_create(sdate,varname,region,sample_path=None):
    assert varname in ['TMP','TMAX','TMIN','R01','RAT','SMG']
    nowtime=datetime.now()
    nowtime=nowtime.strftime('%Y%m%d%H%M%S')
    if varname in ['TMP','R01']:last_tag='02401'
    if varname in ['TMAX','TMIN']:last_tag='02424'
    if varname in ['RAT','SMG']:last_tag='01201'
    fname= f'Z_NWGD_C_{region}_{nowtime}_P_OGFP_SPFC-{varname}_{sdate}_{last_tag}.GRB2'
    # sample_name=f'Z_NWGD_C_BECS_YYYYmmddHHMMSS_P_OGFP_SPFC-{varname}_YYYYmmddHHMM_{last_tag}.GRB2'
    sample_name=f'Z_NWGD_C_BECS_*_P_OGFP_SPFC-{varname}_*_*.GRB2'
    if sample_path is None:sample_path='./'
    sample_name=glob(os.path.join(sample_path,sample_name))[0]
    return fname,sample_name

def write_grib(sdate, data, varname, extent, region, sample_path, save_path,
        check_name=None, ftimes=None, step=0.01, round_decimal=2,
        save_name=None,sample_name=None):
    """
    运行函数，用于改写grib数据并保存。

    参数：
    sdate (str): 开始日期，格式为'YYYYMMDD'。
    data (dict): 区域数据，numpy数组。
    varname (str): 要处理的变量名，文件名中变量名一致。
    extent (tuple): 数据的经纬度范围，格式为(min_lat, max_lat, min_lon, max_lon)。
    region (str): 区域标识。
    sample_path (str): 模板数据所在路径。
    save_path (str): 保存修改后数据的路径。
    check_name (str, 可选): 检查的变量名（grib文件内完整变量名）。默认为None。
    ftimes (list, 可选): 预报时次列表。默认为None。
    step (float, 可选): 空间分辨率。默认为0.01。
    round_decimal (int, 可选): 经纬度保留的小数位数。默认为2。
    返回：
    无
    """
    check_data(extent,data,varname,step=step,round_decimal=round_decimal)
    if save_name is None:
        save_name, grid_name = name_create(sdate, varname, region,sample_path=sample_path)  # 获取文件名
    if sample_name is None:sample_name=grid_name
    # 模板数据位置
    # sample_name = os.path.join(sample_path, sample_name)
    save_name = os.path.join(save_path, save_name)
    # 开始改写grib数据，并保存
    _write_grib(sdate, data, varname, extent,gribfile=sample_name, OutFile=save_name, check_name=check_name,
               ftimes=ftimes, step=step, round_decimal=round_decimal)

def check_data(extent,data,varname,step=0.01,round_decimal=2):
    lat_grid = np.round(np.arange(extent[0], extent[1] + step / 10., step), round_decimal)
    lon_grid = np.round(np.arange(extent[2], extent[3] + step / 10., step), round_decimal)
    dlats,dlons=data.shape[-2:]
    assert dlats==len(lat_grid) and dlons==len(lon_grid) , f'纬向和经向格点数（{len(lat_grid)}，{len(lon_grid)}）与data({data.shape[-2:]})不匹配'
    if varname in ['TMP','R01']:assert data.shape[0]==24 , f'data预报时次数为：{data.shape[0]},{varname}应为24'
    if varname in ['TMAX','TMIN']:
        if data.ndim>2:
            assert data.shape[0]==1 , f'data预报时次数为：{data.shape[0]},{varname}应为1'
    if varname in ['RAT','SMG']:assert data.shape[0]==12 , f'data预报时次数为：{data.shape[0]},{varname}应为12'


############仅修以下参数###############
if __name__ == '__main__':
# 示例：
    #设置常用参数
    sample_path='./sample' #模板路径
    region='CCCC' # 本地区域标识
    extent=(26,28,110,112)  # 本地区域经纬度范围
    save_path='./output' # 保存路径

    #设置动态参数（每次必须按此修改）
    sdate='202403192000' # 起报时间，格式为'YYYYMMDDHHMM'
    data=np.ones((1,201,201)) # 本地区域数据，维度为(时次数,纬向格点数,经向格点数)
    varname='TMAX' # 变量名称['TMP','TMAX','TMIN','R01','RAT','SMG']
    # 开始运行
    check_data(extent,data,varname)
    write_grib(sdate,data,varname,extent,region,sample_path,save_path)


'''
    文件名说明：
    （一）温度格点预报
    24小时内逐小时气温预报：
    Z_NWGD_C_CCCC_YYYYMMDDhhmmss_P_OGFP_SPFC-TMP_YYYYMMDDhhmm_02401.GRB2
    24小时内最高气温预报：
    Z_NWGD_C_CCCC_YYYYMMDDhhmmss_P_OGFP_SPFC-TMAX_YYYYMMDDhhmm_02424.GRB2
    24小时内最低气温预报：
    Z_NWGD_C_CCCC_YYYYMMDDhhmmss_P_OGFP_SPFC-TMIN_YYYYMMDDhhmm_02424.GRB2
    （二）降水格点预报
    24小时内逐小时降水预报：
    Z_NWGD_C_CCCC_YYYYMMDDhhmmss_P_OGFP_SPFC-R01_YYYYMMDDhhmm_02401.GRB2
    （三）强对流格点预报
    12小时内逐小时短时强降水预报：
    Z_NWGD_C_CCCC_YYYYMMDDhhmmss_P_OGFP_SPFC-RAT_YYYYMMDDhhmm_01201.GRB2
    12小时内逐小时雷暴大风预报：
    Z_NWGD_C_CCCC_YYYYMMDDhhmmss_P_OGFP_SPFC-SMG_YYYYMMDDhhmm_01201.GRB2
'''