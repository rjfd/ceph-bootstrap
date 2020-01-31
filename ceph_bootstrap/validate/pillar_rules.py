class ConfigValidationError(Exception):
    def __init__(self, minion, error_msg):
        super(ConfigValidationError, self).__init__("[{}] {}".format(minion, error_msg))


def validate_grains(grains):
    if 'ceph-salt' not in grains:
        raise ConfigValidationError(grains['id'], "'ceph-salt' key not present in grains")

    if 'member' not in grains['ceph-salt'] or not grains['ceph-salt']['member']:
        raise ConfigValidationError(grains['id'], "'member' key not present in grains['ceph-salt']")

    if 'roles' not in grains['ceph-salt']:
        raise ConfigValidationError(grains['id'], "'roles' key not present in grains['ceph-salt']")

    if not isinstance(grains['ceph-salt']['roles'], list):
        raise ConfigValidationError(grains['id'], "grains['ceph-salt:roles'] has an invalid value. "
                                                  "Value must be a list")

    for role in grains['ceph-salt']['roles']:
        if role not in ['mon', 'mgr', 'storage', 'rgw', 'mds', 'iscsi', 'ganesha']:
            raise ConfigValidationError(grains['id'],
                                        "Invalid role '{}' in grains['ceph-salt:roles']"
                                        .format(role))


def validate_pillar_schema(pillar, grains):
    if 'ceph-salt' not in pillar:
        raise ConfigValidationError(grains['id'], "'ceph-salt' key not present in the pillar")

    ceph_pillar = pillar['ceph-salt']
    if not isinstance(ceph_pillar, dict):
        raise ConfigValidationError(grains['id'], "pillar['ceph-salt'] has an invalid value. "
                                                  "Value must be a dict")

    if 'bootstrap_minion' not in ceph_pillar:
        raise ConfigValidationError(grains['id'],
                                    "bootstrap_minion not defined in pillar['ceph-salt]")




def validate_bootstrap_minion(pillar, grains, minion_list):
    if 'bootstrap_minion' not in pillar['ceph-salt']:
        raise ConfigValidationError(grains['id'], "bootstrap_minion not defined in pillar")

    if grains['id'] == pillar['ceph-salt']['bootstrap_minion']:
        if pillar['ceph-salt']['bootstrap_minion'] not in minion_list:
        raise ConfigValidationError(grains['id'],
                                    "bootstrap_minion '{}' does not reference a minion of the Ceph"
                                    " cluster".format(pillar['ceph-salt']['bootstrap_minion']))

        if 'mgr' not in grains['ceph-salt']['roles']:
            raise ConfigValidationError(grains['id'],
                                        "bootstrap_minion '{}' does not have the mgr role")
        if 'mon' not in grains['ceph-salt']['roles']:
            raise ConfigValidationError(grains['id'],
                                        "bootstrap_minion '{}' does not have the mon role")
