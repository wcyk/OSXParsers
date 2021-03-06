import argparse
import datetime
import pprint
import struct

__author__ = 'yk'
__version__ = '.20160925'
__reference__ = 'http://cpansearch.perl.org/src/WIML/Mac-Alias-Parse-0.20/Parse.pm'


RecordTypesV2 = ["folderName", "parentInodePath", "filePath", "appleshare_zoneName",
                 "appleShare_serverName", "appleShare_username", "driverName", "", "", "network_mountInfo",
                 "appleRemoteAccess_dialupInfo", "", "", "", "fileName_utf16", "volName_utf16", "volCreationDate_utc",
                 "fileCreationDate_utc", "filePath_posix", "mountPoint_posix", "aliasOfDMG", "userHome_posix"]
RecordTypesV3 = ["", "parentInodePath", "", "", "", "", "", "", "", "", "", "", "", "", "fileName_utf16", "volName_utf16",
                 "", "", "filePath", "volMountPoint"]
HFS_to_Epoch = 2082844800


class AliasRecord:
    type = 0
    length = 0
    data = None


class AliasData:
    class Header:
        type_user = None  # ignore
        length = 0
        version = 0
        kind_item = 0  # file or folder

    class Volume:
        length = 0  # v2 only
        name = ""  # v2 only
        date_creation = 0  # local time
        type_fs = ''
        type_vol = 0  # v2 only

    class Item:
        inode_pfolder = 0
        len_filename = 0  # v2 only
        name = ""  # v2 only
        inode = 0
        date_creation = 0
        creator_code = None  # v2 only; ignore
        type = None  # v2 only; ignore
        levels_from = 0  # v2 only; ignore
        levels_to = 0  # v2 only; ignore

    vol_attr_flags = None  # v2 only; ignore
    vol_fsid = None  # v2 only; ignore

    records = []


def parse(raw_data):
    result.clear()
    alias_data = AliasData()
    alias_data.header = AliasData.Header()
    alias_data.item = AliasData.Item()
    alias_data.volume = AliasData.Volume()

    # header
    alias_data.header.type_user = struct.unpack('4s', raw_data[0:4])[0]
    alias_data.header.length = struct.unpack('>H', raw_data[4:6])[0]
    alias_data.header.version = struct.unpack('>H', raw_data[6:8])[0]
    alias_data.header.kind_item = struct.unpack('>H', raw_data[8:10])[0]

    if alias_data.header.version == 2:
        raw_data = __parse_v2(raw_data, alias_data)
    elif alias_data.header.version == 3:
        raw_data = __parse_v3(raw_data, alias_data)

    alias_data.records = []
    while True:
        record = AliasRecord()
        record.type = struct.unpack('>h', raw_data[0:2])[0]
        record.length = struct.unpack('>H', raw_data[2:4])[0]
        record.data = struct.unpack(str(record.length) + 's', raw_data[4:4 + record.length])[0]
        alias_data.records.append(record)

        raw_data = raw_data[2 + 2 + record.length:]
        if (2 + 2 + record.length) % 2 != 0:
            raw_data = raw_data[1:]
        if record.type == -1:  # end of list
            break

    if alias_data.header.version == 2:
        __interpret_v2(alias_data)
        # __debug_v2(alias_data)
    elif alias_data.header.version == 3:
        __interpret_v3(alias_data)
        # __debug_v3(alias_data)

    return result


def __parse_v2(raw_data, alias_data):
    # volume details
    alias_data.volume.length = struct.unpack('>B', raw_data[10:11])[0]
    alias_data.volume.name = struct.unpack(str(alias_data.volume.length) + 's',
                                           raw_data[11:11 + alias_data.volume.length])[0]
    alias_data.volume.date_creation = struct.unpack('>I', raw_data[38:42])[0]
    alias_data.volume.type_fs = struct.unpack('2s', raw_data[42:44])[0]
    alias_data.volume.type_vol = struct.unpack('>H', raw_data[44:46])[0]

    # item details
    alias_data.item.inode_pfolder = struct.unpack('>I', raw_data[46:50])[0]
    alias_data.item.len_filename = struct.unpack('>B', raw_data[50:51])[0]
    alias_data.item.name = struct.unpack(str(alias_data.item.len_filename) + 's',
                                         raw_data[51:51 + alias_data.item.len_filename])[0]
    alias_data.item.inode = struct.unpack('>I', raw_data[114:118])[0]
    alias_data.item.date_creation = struct.unpack('>I', raw_data[118:122])[0]
    alias_data.item.creator_code = struct.unpack('4s', raw_data[122:126])[0]
    alias_data.item.type = struct.unpack('4s', raw_data[126:130])[0]
    alias_data.item.levels_from = struct.unpack('>h', raw_data[130:132])[0]
    alias_data.item.levels_to = struct.unpack('>h', raw_data[132:134])[0]

    # others
    alias_data.vol_attr_flags = struct.unpack('4s', raw_data[134:138])[0]
    alias_data.vol_fsid = struct.unpack('2s', raw_data[138:140])[0]

    # records
    return raw_data[150:]


def __parse_v3(raw_data, alias_data):
    # volume details
    alias_data.volume.date_creation = struct.unpack('>I', raw_data[12:16])[0]
    alias_data.volume.type_fs = struct.unpack('2s', raw_data[18:20])[0]

    # item details
    alias_data.item.inode_pfolder = struct.unpack('>I', raw_data[24:28])[0]
    alias_data.item.inode = struct.unpack('>I', raw_data[28:32])[0]
    alias_data.item.date_creation = struct.unpack('>I', raw_data[34:38])[0]

    # records
    return raw_data[58:]


def __interpret_v2(alias_data):
    if alias_data.header.kind_item == 0:
        result['fileKind'] = "file"
    elif alias_data.header.kind_item == 1:
        result['fileKind'] = "folder"

    result['fileInode'] = alias_data.item.inode
    result['parentInode'] = alias_data.item.inode_pfolder
    result['volName'] = alias_data.volume.name
    result['volCreationDate'] = datetime.datetime.utcfromtimestamp(alias_data.volume.date_creation -
                                                                   HFS_to_Epoch).strftime('%d %b %Y %H:%M:%S')
    result['volFileSystem'] = alias_data.volume.type_fs

    if alias_data.volume.type_vol == 0:
        result['volType'] = "fixed HD"
    elif alias_data.volume.type_vol == 1:
        result['volType'] = "network disk"
    elif alias_data.volume.type_vol == 2:
        result['volType'] = "400KB floppy"
    elif alias_data.volume.type_vol == 3:
        result['volType'] = "800KB floppy"
    elif alias_data.volume.type_vol == 4:
        result['volType'] = "1.4MB floppy"
    elif alias_data.volume.type_vol == 5:
        result['volType'] = "other ejectable media"

    result['fileName'] = alias_data.item.name
    result['fileCreationDate'] = datetime.datetime.utcfromtimestamp(alias_data.item.date_creation -
                                                                    HFS_to_Epoch).strftime('%d %b %Y %H:%M:%S')

    for record in alias_data.records:
        if record.type == 1:
            inode_components = []
            count_components = int(record.length / 4)
            for _ in range(count_components):
                inode_components.append(struct.unpack('>I', record.data[0:4])[0])
                record.data = record.data[4:]

            result[RecordTypesV2[1]] = ""
            for inode in reversed(inode_components):
                result[RecordTypesV2[1]] += str(inode) + '/'
        if record.type == 2:
            result[RecordTypesV2[2]] = record.data.replace(b':', b'/')
        elif record.type == 14:
            result[RecordTypesV2[14]] = (record.data[1:] + b'\x00').decode('utf-16')
        elif record.type == 15:
            result[RecordTypesV2[15]] = (record.data[1:] + b'\x00').decode('utf-16')
        elif record.type == 16:
            result[RecordTypesV2[16]] = datetime.datetime.utcfromtimestamp(
                struct.unpack('>I', record.data[2:-2])[0] - HFS_to_Epoch).strftime('%d %b %Y %H:%M:%S')
        elif record.type == 17:
            result[RecordTypesV2[17]] = datetime.datetime.utcfromtimestamp(
                struct.unpack('>I', record.data[2:-2])[0] - HFS_to_Epoch).strftime('%d %b %Y %H:%M:%S')


def __interpret_v3(alias_data):
    if alias_data.header.kind_item == 0:
        result['fileKind'] = "file"
    elif alias_data.header.kind_item == 1:
        result['fileKind'] = "folder"

    result['volCreationDate'] = datetime.datetime.utcfromtimestamp(alias_data.volume.date_creation -
                                                                   HFS_to_Epoch).strftime('%d %b %Y %H:%M:%S')
    result['parentInode'] = alias_data.item.inode_pfolder
    result['fileInode'] = alias_data.item.inode
    result['volFileSystem'] = alias_data.volume.type_fs
    result['fileCreationDate'] = datetime.datetime.utcfromtimestamp(alias_data.item.date_creation -
                                                                    HFS_to_Epoch).strftime('%d %b %Y %H:%M:%S')

    for record in alias_data.records:
        if record.type == 1:
            inode_components = []
            count_components = int(record.length / 4)
            for _ in range(count_components):
                inode_components.append(struct.unpack('>I', record.data[0:4])[0])
                record.data = record.data[4:]

            result[RecordTypesV3[1]] = ""
            for inode in reversed(inode_components):
                result[RecordTypesV3[1]] += str(inode) + '/'
        elif record.type == 14:
            result[RecordTypesV3[14]] = (record.data[1:] + b'\x00').decode('utf-16')
        elif record.type == 15:
            result[RecordTypesV3[15]] = (record.data[1:] + b'\x00').decode('utf-16')
        elif record.type == 18:
            result[RecordTypesV3[18]] = record.data
        elif record.type == 19:
            result[RecordTypesV3[19]] = record.data


def __debug_v2(alias_data):
    print("{}".format("===== Header ====="))
    print("Length       : {}".format(alias_data.header.length))
    print("Version      : {}".format(alias_data.header.version))
    print("Item Kind    : {} (0 = file, 1 = folder)".format(alias_data.header.kind_item))

    print("{}".format("===== Volume ====="))
    print("Length       : {}".format(alias_data.volume.length))
    print("Name         : {}".format(alias_data.volume.name.decode('utf-8')))
    print("Date Creation: {}".format(alias_data.volume.date_creation))
    print("FS Type      : {}".format(alias_data.volume.type_fs.decode('utf-8')))
    print("Volume Type  : {}".format(alias_data.volume.type_vol) + " (0 = fixed HD, 1 = network disk, 2 = 400KB FD, "
                                                                   "3 = 800KB FD, 4 = 1.4MB FD, "
                                                                   "5 = other ejectable media)")
    
    print("{}".format("===== Item ====="))
    print("Pfolder Inode: {}".format(alias_data.item.inode_pfolder))
    print("Name         : {}".format(alias_data.item.name.decode('utf-8')))
    print("Inode        : {}".format(alias_data.item.inode))
    print("Date Creation: {}".format(alias_data.item.date_creation))
    print("Levels from  : {}".format(alias_data.item.levels_from))
    print("Levels to    : {}".format(alias_data.item.levels_to))
    print("{}".format("================"))


def __debug_v3(alias_data):
    print("{}".format("===== Header ====="))
    print("Length       : {}".format(alias_data.header.length))
    print("Version      : {}".format(alias_data.header.version))
    print("Item Kind    : {} (0 = file, 1 = folder)".format(alias_data.header.kind_item))

    print("{}".format("===== Volume ====="))
    print("Date Creation: {}".format(alias_data.volume.date_creation))
    print("FS Type      : {}".format(alias_data.volume.type_fs.decode('utf-8')))

    print("{}".format("===== Item ====="))
    print("Pfolder Inode: {}".format(alias_data.item.inode_pfolder))
    print("Inode        : {}".format(alias_data.item.inode))
    print("Date Creation: {}".format(alias_data.item.date_creation))
    print("{}".format("================"))


result = {}

parser = argparse.ArgumentParser(description="Parse alias data")
parser.add_argument('raw', metavar='alias', type=str, nargs=1, help="specify path to file that contains raw alias data")
args = parser.parse_args()

with open(args.raw[0], 'rb') as raw_alias:
    file_content = raw_alias.read()
    parse(file_content)
pprint.pprint(result)
