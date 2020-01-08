const models = require('../models')
const { logger } = require('../logging')
const { publishAnnouncement } = require('../awsSNS')
const axios = require('axios')
const config = require('../config.js')

async function pushAnnouncementNotifications () {
  try {
    logger.info('pushAnnouncementNotifications')
    // Read-only tx
    const tx = await models.sequelize.transaction()
    const audiusNotificationUrl = config.get('audiusNotificationUrl')
    logger.info(audiusNotificationUrl)
    // TODO: move below to index-mobile.json
    const response = await axios.get(`${audiusNotificationUrl}/index.json`)
    logger.info(response.data)
    if (response.data && Array.isArray(response.data.notifications)) {
      // TODO: Worth slicing?
      for (var notif of response.data.notifications) {
        processAnnouncement(notif, tx)
      }
    }
  } catch (e) {
    logger.error(`pushAnnouncementNotifications ${e}`)
  }
}

async function processAnnouncement (notif, tx) {
  if (notif.type !== 'announcement') { return }
  let pushedNotifRecord = await models.PushedAnnouncementNotifications.findAll({
    where: {
      announcementId: notif.id
    }
  })
  let pendingNotificationPush = pushedNotifRecord.length === 0
  if (!pendingNotificationPush) { return }
  await _pushAnnouncement(notif, tx)
}

async function _pushAnnouncement (notif, tx) {
  logger.info(`Sending notification ${notif.id}`)
  logger.info(`------------------------`)
  const audiusNotificationUrl = config.get('audiusNotificationUrl')
  const notifUrl = `${audiusNotificationUrl}/${notif.id}.json`
  const response = await axios.get(notifUrl)
  const details = response.data
  const msg = details.shortDescription
  logger.info(details)
  logger.info(details.shortDescription)
  // Push notification to all users with a valid device token at this time
  let validDeviceRecords = await models.NotificationDeviceToken.findAll({
    where: {
      enabled: true
    }
  })
  await Promise.all(validDeviceRecords.map((device) => {
    logger.info(`Sending ${notif.id} to ${JSON.stringify(device)}`)
    // TODO: PUSH  notif here
  }))

  logger.info(`------------------------`)
  // Update database record with notifiation id
  // await models.PushedAnnouncementNotifications.create({ announcementId: notif.id })
}

module.exports = { pushAnnouncementNotifications }