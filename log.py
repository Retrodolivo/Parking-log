import serial
import math
from datetime import datetime
from tabulate import tabulate
import argparse
import sys

argParser = argparse.ArgumentParser(add_help=False)
argParser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                       help='Script for gathering log data from Scooter Parking.'
                            'There are 2 options of getting raw data:'
                            '1. Download it via USB(vcp), but dont forget to provide port name before.  '
                            '2. Provide raw flash binary file to script. It must comprise only log data part')
argParser.add_argument("-p", "--port", help='Enter device port name. '
                                            'Examples: Windows - "COMx"; Linux - "dev/ttyUSBx" x - port number.')
argParser.add_argument("-f", "--file", help='add path to binary log data')
args = argParser.parse_args()


actions = {'NO_ACTION': {'log_val': 1,
                         'text': 'НЕТ ДЕЙСТВИЯ'},
           'LOCK_IDLE': {'log_val': 2,
                         'text': 'ПАРКОВКА ЗАКРЫЛАСЬ'},
           'UNLOCK_IDLE': {'log_val': 3,
                           'text': 'ПАРКОВКА ОТКРЫЛАСЬ'},
           'LOCK_CELL': {'log_val': 4,
                         'text': 'ЯЧЕЙКА ЗАКРЫЛАСЬ'},
           'UNLOCK_CELL': {'log_val': 5,
                           'text': 'ЯЧЕЙКА ОТКРЫЛАСЬ'},
           'NO_ACCESS_IN_IDLE': {'log_val': 50,
                                 'text': 'НЕТ ДОСТУПА - КАРТА НЕИЗВЕСТНА'},
           'NO_ACCESS_NO_NET': {'log_val': 51,
                                'text': 'НЕТ ДОСТУПА - ОШИБКА СЕТИ'},
           'NO_NET': {'log_val': 52,
                      'text': 'ОШИБКА СЕТИ'},
           }
# 1.Timestamp(32bit);
# 2.CardID(32bit);
# 3.Index(16bit);
# 4.Action(8bit);
# 5.Cell_num(8bit).
log_record = {'Timestamp': {'size': 4},
              'CardID': {'size': 4},
              'Index': {'size': 2},
              'Action': {'size': 1},
              'Cell_num': {'size': 1}
              }
# Set according to expected log data arrangement
flash = {'total pages': 0,
         'bytes per page': 2048,
         'bytes per record': sum(d['size'] for d in log_record.values() if d),
         'records per page': 0,
         'record arrangement': ('Timestamp', 'CardID', 'Index', 'Action', 'Cell_num')
         }
flash['records per page'] = math.floor(flash['bytes per page'] / flash['bytes per record'])

flash_list = []
flash_str = b''
dev_sernum = 0


def main(option, arg):
    global log_record
    global flash
    global flash_list
    global flash_str
    global dev_sernum

    match option:
        case 'file':
            # get binary string then convert it to list
            f = open(arg, 'rb')
            flash_str = f.read()
            f.close()
            flash['total pages'] = math.floor(len(flash_str) / flash['bytes per page'])
            if flash['total pages'] < 1:
                print("bin file should be at least 1 page size")
            else:
                flash_list.extend(flash_str)
                log_record_list = []
                for page in range(flash['total pages']):
                    for record in retrieve_log_records_from_page(page, True):
                        log_record_list.append(record)
                print(*log_record_list, sep='\n')
                print_records(log_record_list)

        case 'port':
            # Serial connection config
            ser = serial.Serial()
            ser.port = arg
            ser.baudrate = 115200
            ser.bytesize = serial.EIGHTBITS
            ser.parity = serial.PARITY_NONE
            ser.stopbits = serial.STOPBITS_ONE
            ser.timeout = None
            ser.open()
            print('\rConnected' if ser.is_open else '\rDisconnected')

            # Download data page by page
            if ser.is_open:
                ser.flush()
                # Str command to device
                command = b'logs'
                ser.write(command)
                dev_sernum = int.from_bytes(ser.read(1), 'little', signed=False)
                print('Serial number: %.4d\n' % dev_sernum)
                flash['total pages'] = int.from_bytes(ser.read(1), 'little', signed=False)
                print('total pages: %d' % flash['total pages'])
                print('downloading...')
                for page in range(flash['total pages']):
                    print('page: %d' % (page + 1))
                    for record in range(flash['records per page']):
                        print('\rDone\n' if record == flash['records per page'] - 1
                              else '\rrecord: %d out of %d' % (record + 1, flash['records per page']), end='')
                        for byte in range(flash['bytes per record']):
                            flash_str += ser.read(1)
            raw_data_file = 'records.bin'
            f = open(raw_data_file, 'wb')
            f.write(flash_str)
            f.close()
            ser.close()
            print('\nConnected' if ser.is_open else '\nDisconnected')
            # decoding process#
            f = open(raw_data_file, 'rb')
            flash_list.extend(flash_str)
            log_record_list = []
            for page in range(flash['total pages']):
                for record in retrieve_log_records_from_page(page, False):
                    log_record_list.append(record)
            print(*log_record_list, sep='\n')
            print_records(log_record_list)


def parse_raw_logs(record_list):
    global actions
    for record in record_list:
        ret_list = []
        index = record['Index']
        ret_list.append(index + 1)
        dt = datetime.fromtimestamp(record['Timestamp'])
        ret_list.append(dt)

        for action in actions.keys():
            if actions[action]['log_val'] == record['Action']:
                ret_list.append(actions[action]['text'])
                break

        card = record['CardID']
        ret_list.append(card)
        match action:
            # TODO replace explicit magic nums with action(dict) nested keys
            # Do not include useless fields in certain actions
            case 2 | 3 | 50 | 51 | 52:
                cell = '---'
            case _:
                cell = record['Cell_num']
        ret_list.append(cell)

        yield ret_list


def print_records(log_record_list):
    print('Серийный номер: %.4d\n' % dev_sernum)
    data = []
    for log in parse_raw_logs(log_record_list):
        data.append(log)
    print(tabulate(data, headers=['#', 'Дата и Время', 'Действие', 'Карта #', 'Ячейка #']))
    output_f = open('logs.txt', 'w')
    output_f.write(tabulate(data, headers=['#', 'Дата и Время', 'Действие', 'Карта #', 'Ячейка #']))
    output_f.close()


def retrieve_log_records_from_page(page, is_raw_flash):
    global log_record
    global flash
    global flash_list
    global flash_str
    temp_list = []  # log element parts would be stored there
    elem_pos = {'start': 0, 'end': 0}
    for record in range(flash['records per page']):
        if is_raw_flash:
            offset = 0 + page * flash['bytes per page']
        else:
            offset = 0 + page * flash['records per page'] * flash['bytes per record']
        ret_dict = {'Timestamp': 0, 'CardID': 0, 'Index': 0, 'Action': 0, 'Cell_num': 0}

        for elem in flash['record arrangement']:
            elem_pos['start'] = offset + record * flash['bytes per record']
            elem_pos['end'] = offset + log_record[elem]['size'] + record * flash['bytes per record']
            temp_list.extend(flash_list[elem_pos['start']:elem_pos['end']])
            offset += log_record[elem]['size']

            for byte in range(log_record[elem]['size']):
                ret_dict[elem] |= temp_list[byte] << 8 * byte
            temp_list.clear()

        yield ret_dict


if __name__ == "__main__":
    if len(sys.argv) == 1:
        argParser.print_help()
    else:
        option = ''
        if args.port is not None:
            option = 'port'
            main(option, args.port)
        elif args.file is not None:
            option = 'file'
            main(option, args.file)
