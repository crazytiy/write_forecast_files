### write_gribfiles.py

利用本地数据修改grib并保存
使用条件：
    1.data:本地区域的数据的numpy数组（空间分辨率0.01°），二维（单预报时次）或三维（多预报时次）
    2.extent:本地区域经纬度范围，需要与data完全对应,格式为(min_lat, max_lat, min_lon, max_lon)
    使用方法:
    修改"if __name__ == '__main__':"下面的部分，按示例修改参数，然后运行即可。
    导入方式调用方法：

```python
from write_gribfiles import write_grib
#设置常用参数
sample_path='./sample' #模板路径
region='CCCC' # 本地区域标识
extent=(26,28,110,112) # 本地区域经纬度范围
save_path='./output' # 保存路径

#设置动态参数（每次必须按此修改）
sdate='202403192000' # 起报时间，格式为'YYYYMMDDHHMM'
data=np.ones((12,201,201)) # 本地区域数据，维度为(时次数,纬向格点数,经向格点数)
varname='SMG' # 变量名称['TMP','TMAX','TMIN','R01','RAT','SMG']

#开始运行
check_data(extent,data,varname)
write_grib(sdate,data,varname,extent,region,sample_path,save_path)
```

### write_stationfile.py

利用本地数据修改站点文件并保存
注意站点文件在./userdata/stations98.csv下面，请核对是否正确
运行流程：
    1. 根据文件名读取已经生成的强对流格点预报数据
    2. 根据station_filename读取站点信息(默认./userdata/stations98.csv),并通过地市名字(city)进行筛选
    3. 根据站点经纬度坐标，将格点插值到站点，生成站点预报
    4. 按照格式将数据写入txt文件
调用方式：

```python
from write_stationfile import write_station
 #设置对流格点预报路径和保存路径（自己生成的格点预报）
 ratfile='短强格点预报路径' #短强格点预报路径
 smgfile='雷暴大风格点预报路径' #雷暴大风格点预报路径
 save_path = './output' # 保存路径
 # 写入强对流数据
 write_station(ratfile,smgfile,save_path,region='CCCC',city='长沙市')
```


    