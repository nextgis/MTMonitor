# coding=utf-8
import requests
from pyproj import Proj, transform
import shapely
from shapely.geometry import Polygon
from shapely.geometry import Point
from shapely.geometry import mapping
import fiona
from fiona.crs import from_epsg
import json
from datetime import datetime

class MTMonitor():

    MT_API_Key = ''
    MT_API_gate = 'https://services.marinetraffic.com/api/exportvessels/v:8'
    default_time_period = 5 # In minutes
    default_run_period = 5  # In minutes
    monitoring_areas = []
    last_vessels_response = []

    def __init__(self, MT_API_Key, mode='Predefined', monitoring_area_source=None):
        """
        Инициализируем класс через ключ АПИ и путь к набору данных с границами, внутри которых наблюдаем суда
        Сразу делаем следующую работу:
        1. Извлекаем все объекты из набора геоданных - получаем их список (используем пакет Fiona)
        2. Перепроецируем их в WGS84 (пакеты Fiona, PyProj)
        3. Для каждого объекта в отдельности считаем bounds в WGS84
        4. Храним всё это дело в свойствах экземпляра класса
        5. Ключ API тоже записываем в свойства

        :param monitoring_area_source: Source for input geodata
        :param MT_API_Key: API Key for MarineTraffic.com API
        """

        self.MT_API_Key = MT_API_Key
        # TODO: Check if API Key is valid

        if mode not in ['Predefined','Custom']:
            print 'Invalid mode. Valid options are: Predefined, Custom. Auto set to Predefined'
            self.mode = 'Predefined'
        else:
            self.mode = mode

        if monitoring_area_source:
            source_dataset = fiona.open(monitoring_area_source)

            source_epsg = source_dataset.crs['init']

            if str(source_epsg).lower() != 'epsg:4326':
                monitoring_area_full_shapes = self.__get_reprojected_vector_dataset_coordinates(source_dataset, source_epsg, 'epsg:4326')
            else:
                monitoring_area_full_shapes = self.__get_raw_vector_dataset_coordinates(source_dataset)

            for feature in monitoring_area_full_shapes:
                self.monitoring_areas.append({'geometry':feature,'bounds':self.__get_bounds_from_coordinates(feature)})


    def get_vessels(self, time_period=None, emulation=True):
        """
        Собственно, получаем список судов. Здесь происходит следующая работа:
        1. Берём список регионов, полученных на этапе инициализации
        2. Для каждого берём bounds, формируем запрос к API с периодом и пространствеными границами
        ! Важно. Поскольку стоимость запроса определяется исходя из количества возвращенных записей, на количестве
        запросов можно не экономить, а экономить на общей опрашиваемой площади
        3. Результаты запроса обрезаем по настоящим границам наших объектов (а пришли они в bounds)
        4. Возвращаем json с итоговым списком полученных судов (или храним в свойстве экземпляра класса,
        например self.last_vessels_response)

        :param time_period: Time to observe vessels in minutes
        """


        ##### EMULATION FOR TESTS

        if emulation:
            vessels = [{"MMSI":"304010417","IMO":"9015462","SHIP_ID":"359396","LAT":"47.758499","LON":"-5.154223","SPEED":"74","HEADING":"329","COURSE":"327","STATUS":"0","TIMESTAMP":"2017-05-19T09:39:57","DSRC":"TER","UTC_SECONDS":"54"},
                       {"MMSI":"215819000","IMO":"9034731","SHIP_ID":"150559","LAT":"47.926899","LON":"-5.531450","SPEED":"122","HEADING":"162","COURSE":"157","STATUS":"0","TIMESTAMP":"2017-05-19T09:44:27","DSRC":"TER","UTC_SECONDS":"28"},
                       {"MMSI":"255925000","IMO":"9184433","SHIP_ID":"300518","LAT":"47.942631","LON":"-5.116510","SPEED":"79","HEADING":"316","COURSE":"311","STATUS":"0","TIMESTAMP":"2017-05-19T09:43:53","DSRC":"TER","UTC_SECONDS":"52"}]

            for vessel_new_response in vessels:
                vessel_new_response['NEW'] = True
                for vessel_last_response in self.last_vessels_response:
                    if vessel_new_response['SHIP_ID'] == vessel_last_response['SHIP_ID']:
                        vessel_new_response['NEW'] = False

            self.last_vessels_response = vessels
            return vessels

        ##### END EMULATION



        if not time_period:
            time_period = self.default_time_period

        vessels_filtered = []

        if self.mode == 'Predefined':
            vessels = self.__marine_traffic_vp_in_predifined_area_request(time_period)
            if self.monitoring_areas:
                for area in self.monitoring_areas:
                    print 'Vessels:'
                    print vessels
                    for vessel in vessels:
                        if self.__point_inside_polygon(float(vessel['LON']), float(vessel['LAT']), area['geometry']):
                            vessels_filtered.append(vessel)
            else:
                vessels_filtered = vessels


        elif self.mode == 'Custom':
            if not self.monitoring_areas:
                print 'Monitoring area must be specified. Provide it with option monitoring_area_source while' \
                      'class object initialization'
                return vessels_filtered
            else:
                for area in self.monitoring_areas:
                    vessels = self.__marine_traffic_vp_in_custom_area_request(time_period,
                                                                       area['bounds']['y_min'],
                                                                       area['bounds']['y_max'],
                                                                       area['bounds']['x_min'],
                                                                       area['bounds']['x_max'])
                    for vessel in vessels:
                        if self.__point_inside_polygon(float(vessel['LON']), float(vessel['LAT']), area['geometry']):
                            vessels_filtered.append(vessel)


        # Записать новый атрибут NEW для тех, которые уже были в last_vessels_response
        for vessel_new_response in vessels_filtered:
            vessel_new_response['NEW'] = True
            for vessel_last_response in self.last_vessels_response:
                if vessel_new_response['SHIP_ID'] == vessel_last_response['SHIP_ID']:
                    vessel_new_response['NEW'] = False

        self.last_vessels_response = vessels_filtered
        return vessels_filtered

    def export_vessels_to_file (self, output_file, output_type='GeoJSON'):
        """
        Записываем полученные объекты в файл

        :param output_file: Path to output file
        :param output_type: Type of output file
        """

        output_schema = {'geometry': 'Point',
                         'properties': {'LAT': 'str',
                                        'LON': 'str',
                                        'SHIP_ID': 'str',
                                        'MMSI': 'str',
                                        'IMO': 'str',
                                        'SPEED': 'str',
                                        'HEADING': 'str',
                                        'COURSE': 'str',
                                        'STATUS': 'str',
                                        'TIMESTAMP': 'str',
                                        'DSRC': 'str',
                                        'UTC_SECONDS':'str',
                                        'NEW': 'str'}}

        output = fiona.open(output_file, 'w', driver=output_type, schema=output_schema, crs=from_epsg(4326))

        for vessel in self.last_vessels_response:
            #print vessel
            coordinate = Point(float(vessel['LON']),float(vessel['LAT']))
            #print float(vessel['LON'])
            print mapping(coordinate)
            properties = {'LAT': vessel['LAT'],
                          'LON': vessel['LON'],
                          'SHIP_ID': vessel['SHIP_ID'],
                          'MMSI': vessel['MMSI'],
                          'IMO': vessel['IMO'],
                          'SPEED': vessel['SPEED'],
                          'HEADING': vessel['HEADING'],
                          'COURSE': vessel['COURSE'],
                          'STATUS': vessel['STATUS'],
                          'TIMESTAMP': vessel['TIMESTAMP'],
                          'DSRC': vessel['DSRC'],
                          'UTC_SECONDS': vessel['UTC_SECONDS'],
                          'NEW': str(vessel['NEW'])}

            output.write({'geometry': mapping(coordinate), 'properties': properties})

        output.close()

    def export_vessels_to_web(self, nextgis_web_api_options):
        """
        Экспортируем полученные объекты в NextGIS Web

        :param nextgis_web_api_options: All necessary API options
        """

    def automated_vessels_to_file (self, output_file, write_mode = 'NF', output_type='GeoJSON', run_period=None, time_period=None):
        """
        Запускаем периодичное получение данных и их запись в файл(ы).
        Три режима создания файлов:
        NF (New File) - на каждый запрос создается новый файл с отметкой времени в названии
        AF (Append File) - на каждый запрос в файл дописываются данные
        RF (Rewrite File) - на каждый запрос файл создаётся заново

        Конфигурируем частоту запуска и обзор по времени

        :param run_period: How often to run method
        :param time_period: Time to observe vessels in minutes
        :param write_mode: Mode of writing new data
        :param output_file: Output file(s) path
        :param output_type: Output file(s) type
        """


    def automated_vessels_to_web(self, nextgis_web_api_options, run_period=None, time_period=None):
        """
        Аналогично автоматически запускаем запись данных черех API NextGIS Web

        :param nextgis_web_api_options: All necessary API options
        :param run_period:  How often to run method
        :param time_period: Time to observe vessels in minutes
        """



    #### Service private methods

    def __marine_traffic_vp_in_custom_area_request (self, timespan, MINLAT, MAXLAT, MINLON, MAXLON):
        print '%s/%s/MINLAT:%s/MAXLAT:%s/MINLON:%s/MAXLON:%s/timespan:%s/protocol:jsono' % (self.MT_API_gate, self.MT_API_Key, MINLAT, MAXLAT, MINLON, MAXLON, timespan)
        r_loaded = []
        r = requests.get('%s/%s/MINLAT:%s/MAXLAT:%s/MINLON:%s/MAXLON:%s/timespan:%s/protocol:json' % (self.MT_API_gate, self.MT_API_Key, MINLAT, MAXLAT, MINLON, MAXLON, timespan))
        r_loaded = json.loads(r.text)
        print r_loaded
        return r_loaded

        # [{"MMSI":"304010417","IMO":"9015462","SHIP_ID":"359396","LAT":"47.758499","LON":"-5.154223","SPEED":"74","HEADING":"329","COURSE":"327","STATUS":"0","TIMESTAMP":"2017-05-19T09:39:57","DSRC":"TER","UTC_SECONDS":"54"},
        # {"MMSI":"215819000","IMO":"9034731","SHIP_ID":"150559","LAT":"47.926899","LON":"-5.531450","SPEED":"122","HEADING":"162","COURSE":"157","STATUS":"0","TIMESTAMP":"2017-05-19T09:44:27","DSRC":"TER","UTC_SECONDS":"28"},
        # {"MMSI":"255925000","IMO":"9184433","SHIP_ID":"300518","LAT":"47.942631","LON":"-5.116510","SPEED":"79","HEADING":"316","COURSE":"311","STATUS":"0","TIMESTAMP":"2017-05-19T09:43:53","DSRC":"TER","UTC_SECONDS":"52"}]
        # https://services.marinetraffic.com/api/exportvessels/v:8/8205c862d0572op1655989d939f1496c092ksvs4/MINLAT:38.20882/MAXLAT:40.24562/MINLON:-6.7749/MAXLON:-4.13721/timespan:10/protocol:json

    def __marine_traffic_vp_in_predifined_area_request(self, timespan):
        print '%s/%s/timespan:%s/protocol:jsono' % (self.MT_API_gate, self.MT_API_Key, timespan)
        r_loaded = []
        r = requests.get('%s/%s/timespan:%s/protocol:json' % (self.MT_API_gate, self.MT_API_Key, timespan))
        print r.text
        r_loaded = json.loads(r.text)
        print r_loaded
        return r_loaded


    def __get_raw_vector_dataset_coordinates(self, fiona_dataset):
        dataset_coordinates = []
        for feature in fiona_dataset:
            current_geometry_type = feature['geometry']['type']
            if current_geometry_type != 'Polygon':
                continue
            dataset_coordinates.append(feature['geometry']['coordinates'][0])
        return dataset_coordinates

    def __get_reprojected_vector_dataset_coordinates (self, fiona_dataset, source_crs_epsg, dest_crs_epsg):
        source = Proj(init=source_crs_epsg)
        dest = Proj(init=dest_crs_epsg)
        new_dataset = []

        for feature in fiona_dataset:
            new_feature_geometry = []
            current_geometry_type = feature['geometry']['type']
            if current_geometry_type != 'Polygon':
                continue
            current_geometry_coordinates = feature['geometry']['coordinates'][0]
            for current_xy in current_geometry_coordinates:
                source_x = current_xy[0]
                source_y = current_xy[1]
                dest_x, dest_y = transform(source, dest,source_x,source_y)
                new_feature_geometry.append((dest_x,dest_y))
            new_dataset.append(new_feature_geometry)

        return new_dataset

    def __get_bounds_from_coordinates(self, coordinates):
        x_coords = [item[0] for item in coordinates]
        y_coords = [item[1] for item in coordinates]
        return ({'x_min': min(x_coords), 'x_max': max(x_coords), 'y_min': min(y_coords), 'y_max': max(y_coords)})

    def __point_inside_polygon(self, point_x, point_y, polygon_coordinates):
        point = Point((point_x,point_y))
        polygon = shapely.geometry.Polygon(polygon_coordinates)
        return polygon.contains(point)


#a = MTMonitor('c889f60d987ade091f0f92c0d714eb6d094302f9',mode='Predefined')
#a.get_vessels(200, emulation=False)
#a.export_vessels_to_file('/home/silent/test_MT2.geojson')
#b = a.get_vessels(200, emulation=True)
#print b
#print a.monitoring_area_full_shapes
#print a.monitoring_areas
#print a.last_vessels_response

#{u'errors': [{u'code': u'4', u'detail': u'SERVICE INACTIVE'}]}
#{u'errors': [{u'code': u'5', u'detail': u'ABOVE SERVICE CALL LIMIT'}]}