#base_url = 'https://mirror.yandex.ru/astra/frozen/1.11_x86-64-ce/repository/pool/main/'  #URL для сбора данных
base_url = 'https://mirror.yandex.ru/elrepo/dud/'
exclude_suffix = (".md5", ".txt", ".gost", ".gpg", ".key", ".asc") #суффиксы файлов, исключаемые из кеширования
base_catalogs = 'base_cat.json' #json-файл для сохранения списка рутовых каталогов для нацеливания поиска
files_list = 'file_data.json' #json-файл для сохранения списка найденных файлов
