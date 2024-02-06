import json

from tango import Database, DbDevInfo

# ex: dev_info_file_name = 'bite_devices_for_inst_' + server_inst + '.json'
# ex: dev_info_file_name = 'bite_devices_for_inst_dell0.json'
# in_json_file_name = 'bite_devices_for_inst_' + server_inst + '.json'
# in_json_file_path = '../etc' # todo
# dev_info_file_name = in_json_file_path + '/' + in_json_file_name


def add_devs(in_json_file_path, in_json_file_name):
    # TODO - possibly create a class out of these tools

    # There is one entry in the list per BITE device (i.e all devices instantiated in all
    # bite servers for this instance)
    dev_info_file_name = in_json_file_path + "/" + in_json_file_name
    dev_info_dict_list = json.load(open(dev_info_file_name))

    db = Database()

    # Add to the tango DB the devices with names in dev_info_dict_list which do
    # not exist in the DB yet:
    added_dev = False
    for dev_info in dev_info_dict_list:
        db_dev_info = DbDevInfo()
        db_dev_info.name = dev_info["name"]
        db_dev_info.klass = dev_info["klass"]
        db_dev_info.server = dev_info["server"]

        db_existing_dev_list = get_existing_devs(db_dev_info.server)

        if db_dev_info.name in db_existing_dev_list:
            # Device exists, no need to create
            continue
        db.add_device(db_dev_info)
        added_dev = True
        print("Added device {} to Tango DB.".format(db_dev_info.name))

    if not added_dev:
        print("No device was added to Tango DB.")


# Get existing devices of a given server:
def get_existing_devs(server_full_name):
    db = Database()
    db_dev_class_list = db.get_device_class_list(server_full_name)
    # print("dev_class_list = {}\n".format(db_dev_class_list))

    db_dev_list = [
        dev
        for dev in db_dev_class_list
        if "/" in dev and not dev.startswith("dserver")
    ]
    # print("db_dev_list = {}\n".format(db_dev_list))
    return db_dev_list


# reset the polling period for all attributes of a given device proxy (dp):
def reset_polling(dp, poll_period):
    attrs = dp.get_attribute_list()

    periods = [(a, dp.get_attribute_poll_period(a)) for a in attrs]

    # print("attributes polling periods list = {}".format(periods))
    dict((a, p) for a, p in periods)
    # print("attributes polling periods dict = {}".format(pp_dict))

    [dp.poll_attribute(aa, poll_period) for aa, vv in periods if vv]

    # enable for debugging only:
    """
    # Get the polled attributes again to verify the change took place:
    periods = [(a, dp.get_attribute_poll_period(a)) for a in attrs]
    print("attributes polling periods list (updated) = {}".format(periods))
    pp_dict = dict((a,p) for a,p in periods if p)
    print("attributes polling periods dict (updated) = {}".format(pp_dict))
    """
