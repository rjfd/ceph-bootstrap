from ..salt_utils import PillarManager


def check_pillar_config():
    PillarManager.reload()
    pillar = PillarManager.pillar_data
