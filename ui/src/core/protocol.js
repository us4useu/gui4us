// @ts-check
/**
 * Wire protocol decoding -- the counterpart of gui4us/view/web/protocol.py.
 *
 * A frame is `[u32 header length][JSON header][payload]`, which lets the WebSocket transport
 * and the anywidget transport carry exactly the same bytes.
 */

/**
 * @typedef {Object} ArrayHeader
 * @property {string} display
 * @property {number} layer
 * @property {number[]} shape
 * @property {string} dtype
 * @property {number} offset
 * @property {number} size
 */

/**
 * @typedef {Object} FrameHeader
 * @property {string} type
 * @property {number} seq
 * @property {number} timestamp
 * @property {ArrayHeader[]} arrays
 */

/**
 * @typedef {Object} DecodedArray
 * @property {ArrayHeader} header
 * @property {Uint8Array|Float32Array} data
 */

/**
 * @typedef {Object} DecodedFrame
 * @property {FrameHeader} header
 * @property {DecodedArray[]} arrays
 */

/**
 * Decodes one binary frame message.
 * @param {ArrayBuffer|Uint8Array} message
 * @returns {DecodedFrame}
 */
export function decodeFrame(message) {
  const buffer = message instanceof Uint8Array ? message.buffer : message;
  const byteOffset = message instanceof Uint8Array ? message.byteOffset : 0;
  const view = new DataView(buffer, byteOffset);
  const headerLength = view.getUint32(0, /* littleEndian */ true);
  const headerBytes = new Uint8Array(buffer, byteOffset + 4, headerLength);
  /** @type {FrameHeader} */
  const header = JSON.parse(new TextDecoder().decode(headerBytes));
  const payloadOffset = byteOffset + 4 + headerLength;
  const arrays = header.arrays.map((arrayHeader) => ({
    header: arrayHeader,
    data: viewArray(buffer, payloadOffset + arrayHeader.offset, arrayHeader),
  }));
  return { header, arrays };
}

/**
 * @param {ArrayBuffer} buffer
 * @param {number} offset
 * @param {ArrayHeader} header
 * @returns {Uint8Array|Float32Array}
 */
function viewArray(buffer, offset, header) {
  const count = header.shape.reduce((a, b) => a * b, 1);
  if (header.dtype === "uint8") {
    return new Uint8Array(buffer, offset, count);
  }
  if (header.dtype === "float32") {
    // Float32Array requires 4-byte alignment, which the payload offset does not guarantee.
    return new Float32Array(buffer.slice(offset, offset + count * 4));
  }
  throw new Error(`Unsupported dtype in frame: ${header.dtype}`);
}

/** Message type constants, mirroring protocol.py. */
export const TYPE = Object.freeze({
  FRAME: "frame",
  DESCRIPTOR: "descriptor",
  STATE: "state",
  ERROR: "error",
  ACTION: "action",
  SET_SETTING: "set_setting",
});
