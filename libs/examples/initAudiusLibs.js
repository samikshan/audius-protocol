const Web3 = require('web3')

const AudiusLibs = require('../src/index')
const dataContractsConfig = require('../data-contracts/config.json')
const ethContractsConfig = require('../eth-contracts/config.json')

const creatorNodeEndpoint = 'http://localhost:4000'
const identityServiceEndpoint = 'http://localhost:7000'
const dataWeb3ProviderEndpoint = 'http://localhost:8545'
const ethWeb3ProviderEndpoint = 'http://localhost:8546'
const isServer = true

async function initAudiusLibs (useExternalWeb3, ownerWalletOverride = null, ethOwnerWalletOverride = null) {
  let audiusLibsConfig
  let ethWallet = ethOwnerWalletOverride === null ? ethContractsConfig.ownerWallet : ethOwnerWalletOverride
  if (useExternalWeb3) {
    const dataWeb3 = new Web3(new Web3.providers.HttpProvider(dataWeb3ProviderEndpoint))
    audiusLibsConfig = {
      // Network id does not need to be checked in the test environment.
      web3Config: AudiusLibs.configExternalWeb3(
        dataContractsConfig.registryAddress,
        dataWeb3,
        /* networkId */ null,
        ownerWalletOverride
      ),
      ethWeb3Config: AudiusLibs.configEthWeb3(
        ethContractsConfig.audiusTokenAddress,
        ethContractsConfig.registryAddress,
        ethWeb3ProviderEndpoint,
        ethWallet
      ),
      discoveryProviderConfig: AudiusLibs.configDiscoveryProvider(true, null),
      // discoveryProviderConfig: AudiusLibs.configDiscoveryProvider(true, new Set(["http://docker.for.mac.localhost:5000"])),
      isServer
    }
  } else {
    audiusLibsConfig = {
      web3Config: AudiusLibs.configInternalWeb3(dataContractsConfig.registryAddress, dataWeb3ProviderEndpoint),
      ethWeb3Config: AudiusLibs.configEthWeb3(
        ethContractsConfig.audiusTokenAddress,
        ethContractsConfig.registryAddress,
        ethWeb3ProviderEndpoint,
        ethContractsConfig.ownerWallet),
      creatorNodeConfig: AudiusLibs.configCreatorNode(creatorNodeEndpoint),
      discoveryProviderConfig: AudiusLibs.configDiscoveryProvider(true),
      identityServiceConfig: AudiusLibs.configIdentityService(identityServiceEndpoint),
      isServer
    }
  }
  let audiusLibs = new AudiusLibs(audiusLibsConfig)

  console.log('int2')
  await audiusLibs.init()
  return audiusLibs
}

module.exports = initAudiusLibs
