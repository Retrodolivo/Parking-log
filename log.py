import math
from datetime import datetime
from tabulate import tabulate


actions = {'NO_ACTION': {'log_val': 1,
                         'text': 'НЕТ ДЕЙСТВИЯ'},
           'LOCK_IDLE': {'log_val': 2,
                         'text': 'ПАРКОВКА ЗАКРЫЛАСЬ'},
           'UNLOCK_IDLE': {'log_val': 3,
                           'text': 'ПАРКОВКА ОТКРЫЛАСЬ'},
           'LOCK_CELL': {'log_val': 4,
                         'text': 'ЯЧЕЙКА ЗАКРЫЛАСЬ'},
           'UNLOCK_CELL': {'log_val' : 5,
                           'text': 'ЯЧЕЙКА ОТКРЫЛАСЬ'},
           'NO_ACCESS_IN_IDLE': {'log_val': 50,
                                 'text': 'НЕТ ДОСТУПА - КАРТА НЕИЗВЕСТНА'},
           'NO_ACCESS_NO_NET': {'log_val': 51,
                                'text': 'НЕТ ДОСТУПА - ОШИБКА СЕТИ'}
           }

def parse_raw_logs(record_list):

    for record in record_list:
        ret_list = []

        index = record['Index']
        ret_list.append(index + 1)

        dt = datetime.fromtimestamp(record['Timestamp'])
        ret_list.append(dt)

        action = record['Action']
        match action:
            case 1:
                ret_list.append(actions['NO_ACTION']['text'])
            case 2:
                ret_list.append(actions['LOCK_IDLE']['text'])
            case 3:
                ret_list.append(actions['UNLOCK_IDLE']['text'])
            case 4:
                ret_list.append(actions['LOCK_CELL']['text'])
            case 5:
                ret_list.append(actions['UNLOCK_CELL']['text'])
            case 50:
                ret_list.append(actions['NO_ACCESS_IN_IDLE']['text'])
            case 51:
                ret_list.append(actions['NO_ACCESS_NO_NET']['text'])

        card = record['CardID']
        ret_list.append(card)
        match action:
            # TODO replace explicit magic nums with action(dict) nested keys
            # Do not include useless fields in certain actions
            case 2 | 3 | 50 | 51:
                cell = '---'
            case _:
                cell = record['Cell_num']
        ret_list.append(cell)

        yield ret_list

def print_records(log_record_list):
    data = []
    for log in parse_raw_logs(log_record_list):
        data.append(log)
    print(tabulate(data, headers=['#', 'Дата и Время', 'Действие', 'Карта #', 'Ячейка #']))
    output_f = open('logs.txt', 'w')
    output_f.write(tabulate(data, headers=['#', 'Дата и Время', 'Действие', 'Карта #', 'Ячейка #']))
    output_f.close()

def retrieve_log_records_from_page(page):
    temp_list = []  # log element parts would be stored there
    elem_pos = {'start': 0, 'end': 0}
    for record in range(records_in_page):
        offset = 0
        ret_dict = {'Timestamp': 0, 'CardID': 0, 'Index': 0, 'Action': 0, 'Cell_num': 0}

        for elem in data_arrangement_list:
            elem_pos['start'] = offset + record * bytes_in_record
            elem_pos['end'] = offset + log_record[elem]['size'] + record * bytes_in_record
            temp_list.extend(data_list[elem_pos['start']:elem_pos['end']])
            offset += log_record[elem]['size']

            for byte in range(log_record[elem]['size']):
                ret_dict[elem] |= temp_list[byte] << 8 * byte
            temp_list.clear()
        yield ret_dict

# 1.Timestamp(32bit);
# 2.CardID(32bit);
# 3.Index(16bit);
# 4.Action(8bit);
# 5.Cell_num(8bit).
log_record = {'Timestamp': {'size': 4,
                            'val': 0},
              'CardID': {'size': 4,
                         'val': 0},
              'Index': {'size': 2,
                        'val': 0},
              'Action': {'size': 1,
                         'val': 0},
              'Cell_num': {'size': 1,
                           'val': 0}
              }
log_record_list = []
# using by below functions for correct parsing. MUST BE MAINTAINED IN CORRECT ORDER
data_arrangement_list = ['Timestamp', 'CardID', 'Index', 'Action', 'Cell_num']

bytes_in_record = sum(d['size'] for d in log_record.values() if d)
bytes_in_page = 2048
records_in_page = math.floor(bytes_in_page / bytes_in_record)

f = open('flash.bin', 'rb')
# get binary string then convert it to list
dump_data = f.read()
f.close()
data_list = []
data_list.extend(dump_data)
pages = len(data_list) / bytes_in_page
# if page is not full
if math.floor(pages) == 0:
    print("bin file should be at least 1 page size")
else:
    for page in range(int(pages)):
        for record in retrieve_log_records_from_page(1):
            log_record_list.append(record)
print(*log_record_list, sep='\n')
print_records(log_record_list)

