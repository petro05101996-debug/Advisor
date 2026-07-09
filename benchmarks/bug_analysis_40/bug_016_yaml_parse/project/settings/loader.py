import yaml
def load(path):
    return yaml.safe_load(open(path))
