import abc


class DataInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def save(self, obj_type, obj):
        pass

    @abc.abstractmethod
    def get(self, obj):
        pass

    @abc.abstractmethod
    def get_items(self, query):
        pass

    @abc.abstractmethod
    def save_minimal(self, table, obj):
        pass

    @abc.abstractmethod
    def atomic_update(self, table, key, update_expression, express_attr_values):
        pass

    @abc.abstractmethod
    def get_by_user_id(self, user_id):
        pass

    @abc.abstractmethod
    def get_all_items(self, obj_type):
        pass

    @abc.abstractmethod
    def get_by_version(self, entity_id, version):
        pass

    @abc.abstractmethod
    def scan_items(self, expression):
        pass
