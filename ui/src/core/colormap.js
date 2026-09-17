// @ts-check
/**
 * 256-entry colour map look-up tables.
 *
 * Python sends one byte per pixel (already clipped to the display's value range), so the colour
 * map is a pure client-side concern. The maps are the matplotlib ones GUI4us configurations
 * commonly use; unknown names fall back to grayscale.
 */

/** @typedef {Uint8ClampedArray} Lut A flat RGBA LUT of 256*4 bytes. */

/**
 * Builds a LUT by interpolating between anchor colours.
 * @param {Array<[number, number, number]>} anchors
 * @returns {Lut}
 */
function interpolate(anchors) {
  const lut = new Uint8ClampedArray(256 * 4);
  const segments = anchors.length - 1;
  for (let i = 0; i < 256; i++) {
    const position = (i / 255) * segments;
    const index = Math.min(Math.floor(position), segments - 1);
    const t = position - index;
    const from = anchors[index];
    const to = anchors[index + 1];
    lut[i * 4 + 0] = from[0] + (to[0] - from[0]) * t;
    lut[i * 4 + 1] = from[1] + (to[1] - from[1]) * t;
    lut[i * 4 + 2] = from[2] + (to[2] - from[2]) * t;
    lut[i * 4 + 3] = 255;
  }
  return lut;
}

const GRAY = interpolate([[0, 0, 0], [255, 255, 255]]);

// Anchor points sampled from the matplotlib maps of the same name.
const LUTS = {
  gray: GRAY,
  grey: GRAY,
  bone: interpolate([[0, 0, 0], [84, 84, 116], [169, 201, 201], [255, 255, 255]]),
  hot: interpolate([[0, 0, 0], [255, 0, 0], [255, 255, 0], [255, 255, 255]]),
  inferno: interpolate([[0, 0, 4], [87, 16, 110], [188, 55, 84], [249, 142, 9], [252, 255, 164]]),
  magma: interpolate([[0, 0, 4], [81, 18, 124], [183, 55, 121], [252, 137, 97], [252, 253, 191]]),
  viridis: interpolate([[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]]),
  jet: interpolate([[0, 0, 128], [0, 0, 255], [0, 255, 255], [255, 255, 0], [255, 0, 0], [128, 0, 0]]),
};

/**
 * @param {string|null|undefined} name
 * @returns {Lut}
 */
export function getColormap(name) {
  if (!name) return GRAY;
  return LUTS[name.toLowerCase()] || GRAY;
}

/** @returns {string[]} the available colour map names */
export function colormapNames() {
  return Object.keys(LUTS);
}

/**
 * Expands a single-channel image into RGBA using a LUT.
 * @param {Uint8Array} gray
 * @param {Lut} lut
 * @param {Uint8ClampedArray} [out] reused output buffer
 * @returns {Uint8ClampedArray}
 */
export function applyColormap(gray, lut, out) {
  const rgba = out && out.length === gray.length * 4
    ? out : new Uint8ClampedArray(gray.length * 4);
  for (let i = 0; i < gray.length; i++) {
    const offset = gray[i] * 4;
    const target = i * 4;
    rgba[target] = lut[offset];
    rgba[target + 1] = lut[offset + 1];
    rgba[target + 2] = lut[offset + 2];
    rgba[target + 3] = lut[offset + 3];
  }
  return rgba;
}
