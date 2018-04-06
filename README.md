# MTMonitor

Python-класс, обеспечивающий взаимодействие с API сервиса AIS MarineTraffic.com
Поддерживаются два типа запросов к API:
  - Запрос судов в заранее определенной области (PS05)
  - Запрос судов в произвольной области (передача границ поиска вместе с запросом, PS06)

Подробности о методах API можно найти в документации:

https://www.marinetraffic.com/ru/ais-api-services/detail/ps05/vessel-positions-in-a-predefined-area

https://www.marinetraffic.com/ru/ais-api-services/detail/ps06/vessel-positions-in-a-custom-area/

## Установка

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

Для работы с PS05 используйте значение поля mode='Custom'

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
'LAT', 'LON', 'SHIP_ID', 'MMSI', 'IMO', 'SPEED', 'HEADING', 'COURSE', 'STATUS', 'TIMESTAMP', 'DSRC', 'UTC_SECONDS', 'NEW',
'REQUEST_TIME'
