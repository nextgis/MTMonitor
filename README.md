# MTMonitor

Python-класс, обеспечивающий взаимодействие с API сервиса AIS MarineTraffic.com
Поддерживаются два типа запросов к API:
  - Запрос судов в заранее определенной области (PS05)
  - Запрос судов в произвольной области (передача границ поиска вместе с запросом, PS06)

Подробности о методах API можно найти в документации:

https://www.marinetraffic.com/ru/ais-api-services/detail/ps05/vessel-positions-in-a-predefined-area

https://www.marinetraffic.com/ru/ais-api-services/detail/ps06/vessel-positions-in-a-custom-area/

## Установка

### Комплектация
Для полноценной работы необходимы два класса: MTMonitor и MT_NGW_init_schemes

Также доступен тестовый набор (в директории data) данных с границами буферной зоны Ненецкого заповедника (1964.geojson)

### Зависимости
Все пакеты, необходимые для работы MTMonitor, доступны в стандартных репозиториях Python:

requests, pyproj, shapely, fiona

## Инициализация
Для начала работы необходимо импортировать класс и создать его экземпляр, указав ключ API, режим работы (соответствующий одному из API-сервисов) и, опционально для PS05 и обязательно для PS06, OGR-источник данных с векторными границами интереса

```python
from MTMonitor import MTMonitor
monitor = MTMonitor('<your API key>',mode='Predefined', monitoring_area_source='data/1694.geojson')
```

Для работы с PS05 используйте значение поля mode='Predifined'

Для работы с PS06 используйте значение поля mode='Custom'

**Важно!** Если при работе с predifined area (PS05) указан OGR-источник данных с границей (monitoring_area_source), то полученные данные будут обрезаться по этим границам. OGR-источник должен содержать полигоны и может быть в любой системе координат с определенным кодом EPSG. Полигонов в наборе может быть любое число.

Далее, в зависимости от сценария работы, вызываются основные методы.

## Единоразовый запрос
Если необходимо произвести запрос один раз, вручную вызывается функция **get_vessels**. Она управляется двумя параметрами:
  - time_period: определяет глубину поиска судов во времени (в минутах) от момента запроса. Это параметр API MarineTraffic.com. Значение по умолчанию: 5 минут.
  - emulation: если установлен как True, то вместо реального запроса у API генерирует 10 случайных судов в районе острова Долгий. Можно использовать для тестирования. По умолчанию False.

Функция записывает в свойство экземпляра класса **self.last_vessels_response** список полученных судов, а также возвращает их.

```python
vessels = monitor.get_vessels(time_period=5, emulation=False)
print vessels # Аналогичное содержание у monitor.last_vessels_response
>>> [{'STATUS': '0', 'REQUEST_TIME': '2018-04-06T16:43:58', 'MMSI': '304010417', 'UTC_SECONDS': '54', 'LON': '59.3205318858', 'IMO': '9015462', 'SHIP_ID': '359396', 'NEW', ...
```

Каждое судно представляет собой словарь с полями:
'LAT', 'LON', 'SHIP_ID', 'MMSI', 'IMO', 'SPEED', 'HEADING', 'COURSE', 'STATUS', 'TIMESTAMP', 'DSRC', 'UTC_SECONDS', 'NEW','REQUEST_TIME'

Все поля наследуются из ответа API MarineTraffic, кроме двух:

NEW - при работе класса в автоматическом режиме помечает как NEW те судна, которых не было в ответе на прошлый запрос

REQUEST_TIME - время UTC, когда был отправлен запрос к API. Полезно, когда все ответы дополняются друг к другу.


Возвращенное содержимое можно использовать в дальнейшей работе. Предусмотрено несколько готовых сценариев.


## Запись результатов в файл

Самый очевидный способ использования данных, полученных от API MarineTraffic.com - это их запись в векторный набор данных. В классе предусмотрено два сценария работы для записи результатов в файл

### Единоразовая запись в файл

Применив к экземпляру класса метод **export_vessels_to_file**, можно записать последнее полученное в результате выполнения метода get_vessels содержимое в OGR набор данных.
При вызове этого метода используются 3 параметра:
  - output_file: путь до файла для записи
  - output_type: название драйвера OGR, по умолчанию "GeoJSON"
  - write_mode: режим записи. Доступны три варианта, **new** - создаём новый файл, **rewrite** - перезаписываем существующий файл, **append** - дописываем объекты к существующему файлу. При вызове вручную new и rewrite эквивалентны.

```python
monitor.export_vessels_to_file(output_file='test.geojson',output_type='GeoJSON',write_mode='rewrite')
```

### Автоматическая запись в файл через указанный интервал времени

Автоматизация может быть разной. Например, можно вызывать через CRON скрипт, который будет вызывать export_vessels_to_file. Также существует встроенный метод **automated_vessels_to_file**, который позволяет запустить скрипт в режиме автоматического выполнения с заданным интервалом.
При вызове этого метода используются параметры:
  - output_file: путь до файла для записи
  - output_type: название драйвера OGR, по умолчанию "GeoJSON"
  - write_mode: режим записи. Доступны три варианта, **new** - создаём новый файл каждый раз, причём для обеспечения уникальности имён к каждому новому файлу добавляется отметка времени, **rewrite** - перезаписываем каждый раз один и тот же файл, **append** - дописываем объекты к указанному файлу (сначала создаём его, если его не было). В данном случае new и rewrite работают принципиально по-разному.
  - run_period: период запуска автоматического запроса к API и записи в файл в минутах.
  - time_period: время глубины поиска судов, опция запроса API MarineTraffic.com
  - emulation: усли установлен как True, то вместо реальных запросов каждый раз генерируются случайные суда в районе острова Долгий
  
```python
monitor.automated_vessels_to_file(output_file='test.geojson',output_type='GeoJSON',write_mode='append',run_period=5,time_period=5,emulation=False)
```


## Запись результатов в NextGIS Web

Для записи результатов в NGW необходимо иметь подходящий ресурс (с правильной структурой для хранения данных о судах). Создать его можно либо из тестового набора данных (data/sample.zip), либо с помощью встроенного метода **init_NGW_resource_for_vessels**

Этот метод вызывается с тремя параметрами:
  - nextgis_web_api_options: словарь, содержащий сведения для подключения к NGW. Включает четыре поля: user, password, url, resource_id
    - user: имя пользователя NGW
    - password: пароль
    - url: адрес веб-ГИС
    - resource_id: адрес **РОДИТЕЛЬСКОГО** ресурса, внутри которого будет создан новый ресурс
    - например: {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':0}
  - display name: display name ресурса в NGW
  - keyname: keyname ресурса в NGW

  
```python
NGW_options = {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':0}
monitor.init_NGW_resource_for_vessels(nextgis_web_api_options=NGW_options, display_name='Vessels', keyname='Vessels')
```

    
В результате создаётся новый ресурс с нужной структурой и простой базовый стиль, чтобы можно было сразу создавать веб-карту.


### Единоразовая запись в NGW

Для единоразовой отправки судов в NGW используется метод **export_vessels_to_web**

Этот метод вызывается с двумя параметрами:
  - nextgis_web_api_options: словарь, содержащий сведения для подключения к NGW. Включает четыре поля: user, password, url, resource_id
    - user: имя пользователя NGW
    - password: пароль
    - url: адрес веб-ГИС
    - resource_id: адрес **собственно ресурса**, в который будет осуществляться запись. **!** Обратите внимание на отличие от инициализации
    - например: {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':25}
  - write_mode: режим записи информации о судах. Поддерживается два варианта
    - rewrite: при вызове из ресурса удаляются все объекты, затем записываются суда, полученные в результате последнего запроса get_vessels
    - append: новые суда добавляются к уже существующим объектам (при этом есть отметки NEW и REQUEST_TIME для работы с сваленными в кучу судами с разных запросов)
   
   
```python
NGW_options = {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':25}
monitor.export_vessels_to_web(nextgis_web_api_options=NGW_options, write_mode='append')
```


### Автоматическая запись в NGW через указанный интервал времени

Зацикленная запись в NGW вызывается методом **automated_vessels_to_web**, который работает аналогично автоматической записи в файл.

При вызове этого метода используются параметры:
  - nextgis_web_api_options: словарь, содержащий сведения для подключения к NGW. Включает четыре поля: user, password, url, resource_id
    - user: имя пользователя NGW
    - password: пароль
    - url: адрес веб-ГИС
    - resource_id: адрес **собственно ресурса**, в который будет осуществляться запись. **!** Обратите внимание на отличие от инициализации
    - например: {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':25}
  - write_mode: режим записи информации о судах. Поддерживается два варианта
    - rewrite: при каждом вызове из ресурса удаляются все объекты, затем записываются суда, полученные в результате последнего запроса get_vessels. То есть каждый раз список судов обновляется
    - append: При каждом запросе новые суда добавляются к уже существующим объектам (при этом есть отметки NEW и REQUEST_TIME для работы с сваленными в кучу судами с разных запросов)
  - run_period: период запуска автоматического запроса к API и записи в NGW в минутах.
  - time_period: время глубины поиска судов, опция запроса API MarineTraffic.com
  - emulation: усли установлен как True, то вместо реальных запросов каждый раз генерируются случайные суда в районе острова Долгий


## Примеры использования

### Автоматическая запись в файл

```python
# Импортируем класс
from MTMonitor import MTMonitor

# Создаем экземпляр, будем работать с predefined area (ps05)
monitor =  MTMonitor('<your API key>',mode='Predefined', monitoring_area_source='data/1694.geojson')

# Запускаем запись в файл.
monitor.automated_vessels_to_file(output_file='vessels.geojson',output_type='GeoJSON',write_mode='new',run_period=5,time_period=5,emulation=False)

# Теперь каждые пять минут будут создаваться файлы с именами вроде vessels_20180402T180403.geojson
```

### Инициализация ресурса в NGW в корневом ресурсе веб-ГИС

```python
# Импортируем класс
from MTMonitor import MTMonitor

# Создаем экземпляр, будем работать с predefined area (ps05)
monitor =  MTMonitor('<your API key>',mode='Predefined', monitoring_area_source='data/1694.geojson')

# Инициализируем ресурс
NGW_options = {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':0}
monitor.init_NGW_resource_for_vessels(nextgis_web_api_options=NGW_options,display_name='Vessels', keyname='Vessels')

# Ресурс создан! Обратите внимание, здесь resource_id - это id родительского ресурса, в котором будем инициализироваться
```


### Одноразовая запись в NGW

```python
# Импортируем класс
from MTMonitor import MTMonitor

# Создаем экземпляр. Будем работать с custom area (ps06)
monitor =  MTMonitor('<your API key>',mode='Custom', monitoring_area_source='data/1694.geojson')

# Получаем список судов
monitor.get_vessels(time_period=200,emulation=False)

# Записываем их в NGW (считаем, что ресурс уже существует)
NGW_options = {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':25}
monitor.export_vessels_to_web(NGW_options,write_mode='rewrite')

# А здесь resource_id - это уже id нашего ресурса с судами
```


### Автоматическая запись в NGW
```python
# Импортируем класс
from MTMonitor import MTMonitor

# Создаем экземпляр, будем работать с predefined area (ps05)
monitor =  MTMonitor('<your API key>',mode='Predefined', monitoring_area_source='data/1694.geojson')

# Запускаем запись в NGW.
NGW_options = {'user':'administrator','password':'your_password','url':'http://ekazakov.nextgis.com','resource_id':25}
monitor.automated_vessels_to_web(nextgis_web_api_options=NGW_options,write_mode='append',run_period=5,time_period=5,emulation=False)

# Теперь каждые пять минут в ресурс будут дописываться результаты запроса к API
```
