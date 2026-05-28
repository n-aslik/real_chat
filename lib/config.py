from configparser import ConfigParser




class Keys:
    def __init__(self):
        with open("lib/private_key.pem", "rb") as priv:
            self.private_key = priv.read()
        with open("lib/public_key.pem","rb") as pub:
            self.public_key = pub.read()
    
def configdb(filename='lib/configs.env', section='postgresql'):
    parser = ConfigParser()
    parser.read(filename, encoding='UTF-8')
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return db