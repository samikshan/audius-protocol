import logging
import os
import json
import contextlib
from urllib.parse import urljoin
import requests
from . import multihash

@contextlib.contextmanager
def cd(path):
    """Context manager that changes to directory `path` and return to CWD
    when exited.
    """
    old_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_path)


def bytes32_to_str(bytes32input):
    bytes32_stripped = bytes32input.rstrip(b"\x00")
    return bytes32_stripped.decode("utf8")


# relationships_to_include is a list of table names that have relationships to be added
# and returned in the model_dict
def query_result_to_list(query_result, relationships_to_include=None):
    results = []
    for row in query_result:
        results.append(model_to_dictionary(row, None, relationships_to_include))
    return results


# Convert a SQLAlchemy model row to a dictionary object and add any relationships
# objects inside the return dictionary
#
# relationships_to_include is a list of table names that have relationships to be added
# and returned in the model_dict
def model_to_dictionary(db_model_obj, exclude_keys=None, relationships_to_include=None):
    """ Converts the given SQLAlchemy model object into a dictionary. """
    model_dict = {}
    if exclude_keys is None:
        exclude_keys = []

    # make sure exclude_keys are actual fields
    possible_keys = db_model_obj.__table__.columns.keys()
    assert set(exclude_keys).issubset(set(possible_keys))

    for column_name in possible_keys:
        if column_name in exclude_keys:
            continue

        model_dict[column_name] = getattr(db_model_obj, column_name)

    return model_dict


# Configures root logger with custom format and loglevel
# All child loggers will inherit settings from root logger as configured in this function
def configure_logging(loglevel_str):
    logger = logging.getLogger("")  # retrieve root logger

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] {%(name)s:%(lineno)d} (%(levelname)s) - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        loglevel = getattr(logging, loglevel_str)
    except AttributeError:
        logger.warning(
            f"{loglevel_str} is not a valid loglevel. Defaulting to logging.WARN"
        )
        loglevel = logging.WARN

    logger.setLevel(loglevel)


def loadAbiValues():
    abiDir = os.path.join(os.getcwd(), "build", "contracts")
    jsonFiles = os.listdir(abiDir)
    loaded_abi_values = {}
    for contractJsonFile in jsonFiles:
        fullPath = os.path.join(abiDir, contractJsonFile)
        with open(fullPath) as f:
            data = json.load(f)
            loaded_abi_values[data["contractName"]] = data
    return loaded_abi_values


def remove_test_file(filepath):
    """ Try and remove a file, no-op if not present """
    try:
        os.remove(filepath)
    except OSError:
        pass


def multihash_digest_to_cid(multihash_digest):
    user_metadata_digest = multihash_digest.hex()
    user_metadata_hash_fn = 18
    buf = multihash.encode(bytes.fromhex(user_metadata_digest), user_metadata_hash_fn)
    return multihash.to_b58_string(buf)

def get_web3_endpoint(shared_config):
    if shared_config["web3"]["port"] != '443':
        web3endpoint = "http://{}:{}".format(
            shared_config["web3"]["host"], shared_config["web3"]["port"]
        )
    else:
        web3endpoint = "https://{}".format(shared_config["web3"]["host"])
    return web3endpoint

def get_discovery_provider_version():
    versionFilePath = os.path.join(os.getcwd(), ".version.json")
    data = None
    with open(versionFilePath) as f:
        data = json.load(f)
    return data


def get_valid_multiaddr_from_id_json(id_json):
    logger = logging.getLogger(__name__)
    # js-ipfs api returns lower case keys
    if 'addresses' in id_json and isinstance(id_json['addresses'], list):
        for multiaddr in id_json['addresses']:
            if ('127.0.0.1' not in multiaddr) and ('ip6' not in multiaddr):
                logger.warning(f'returning {multiaddr}')
                return multiaddr

    # py-ipfs api returns uppercase keys
    if 'Addresses' in id_json and isinstance(id_json['Addresses'], list):
        for multiaddr in id_json['Addresses']:
            if ('127.0.0.1' not in multiaddr) and ('ip6' not in multiaddr):
                logger.warning(f'returning {multiaddr}')
                return multiaddr
    return None

def get_ipfs_info_from_cnode_endpoint(url, self_multiaddr):
    logger = logging.getLogger(__name__)
    logger.warning(self_multiaddr)
    id_url = urljoin(url, 'ipfs_peer_info')
    data = {'caller_ipfs_id' : self_multiaddr}
    resp = requests.get(
        id_url,
        timeout=5,
        params=data
    )
    json_resp = resp.json()
    valid_multiaddr = get_valid_multiaddr_from_id_json(json_resp)
    if valid_multiaddr is None:
        raise Exception('Failed to find valid multiaddr')
    return valid_multiaddr

def update_ipfs_peers_from_user_endpoint(update_task, cnode_url_list):
    logger = logging.getLogger(__name__)
    if cnode_url_list is None:
        return
    redis = update_task.redis
    cnode_entries = cnode_url_list.split(',')
    interval = int(update_task.shared_config["discprov"]["peer_refresh_interval"])
    for cnode_url in cnode_entries:
        if cnode_url == '':
            continue
        try:
            own_multiaddr = update_task.ipfs_client.ipfs_id_multiaddr()
            logger.warning(f"self multiaddr : {own_multiaddr}")
            multiaddr = get_ipfs_info_from_cnode_endpoint(
                cnode_url,
                update_task.ipfs_client.ipfs_id_multiaddr()
            )
            update_task.ipfs_client.connect_peer(multiaddr)
            redis.set(cnode_url, multiaddr, interval)
        except Exception as e:  # pylint: disable=broad-except
            logger.warning(f"Error connecting to {cnode_url}, {e}")
