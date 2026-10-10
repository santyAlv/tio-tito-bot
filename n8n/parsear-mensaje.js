const body = $input.first().json.body || $input.first().json;

const data = body.data || body;
const key = data.key || {};
const message = data.message || {};

const rawJid = key.remoteJid || '';
let remoteJid = rawJid;

if (rawJid.endsWith('@lid') && key.remoteJidAlt) {
  remoteJid = key.remoteJidAlt;
} else if (rawJid.endsWith('@lid') && key.senderPn) {
  remoteJid = `${key.senderPn}@s.whatsapp.net`;
}

let enviarA = rawJid;
if (rawJid.endsWith('@lid') && key.remoteJidAlt) {
  enviarA = key.remoteJidAlt;
} else if (remoteJid) {
  enviarA = remoteJid;
}

const fromMe = key.fromMe || false;
const messageId = key.id || '';
const pushName = data.pushName || 'Desconocido';

function extraerTexto(msg) {
  if (!msg) return '';
  if (msg.conversation) return msg.conversation;
  if (msg.extendedTextMessage?.text) return msg.extendedTextMessage.text;
  if (msg.imageMessage?.caption) return msg.imageMessage.caption;
  if (msg.videoMessage?.caption) return msg.videoMessage.caption;
  return '';
}

const texto = extraerTexto(message);
const ctx = message.extendedTextMessage?.contextInfo
  || message.imageMessage?.contextInfo
  || message.videoMessage?.contextInfo
  || message.stickerMessage?.contextInfo
  || {};

const quoted = ctx.quotedMessage || null;
const quotedText = extraerTexto(quoted);
const quotedParticipant = ctx.participant || ctx.quotedParticipant || '';
const mentionedJid = ctx.mentionedJid || [];

// Solo marcamos que HAY un reply. Cerebro decide si el citado es de Tío Tito.
const esReplyBot = false;

const esGrupo = remoteJid.endsWith('@g.us') || rawJid.endsWith('@g.us');
const esPrivado = remoteJid.endsWith('@s.whatsapp.net') || rawJid.endsWith('@lid');
const remitenteJid = data.participant || remoteJid || rawJid;

return [{
  json: {
    remoteJid,
    enviarA,
    rawJid,
    fromMe,
    messageId,
    pushName,
    texto,
    esGrupo,
    esPrivado,
    remitenteJid,
    quotedText,
    quotedParticipant,
    mentionedJid,
    esReplyBot,
    procesar: (esGrupo || esPrivado) && !fromMe && texto.length > 0
  }
}];
