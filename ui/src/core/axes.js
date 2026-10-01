// @ts-check
/**
 * Plot axes: the ticks and the frame drawn around an image, the way an ultrasound image is
 * usually shown (OX across, OZ down, in millimetres).
 */

/** Space (CSS px) reserved around the plotting area for the axes. */
export const AXIS_MARGIN = { left: 58, right: 14, top: 26, bottom: 44 };

const AXIS_COLOUR = "#9aa0aa";
const LABEL_COLOUR = "#d4d7dd";
const FONT = "11px system-ui, sans-serif";

/**
 * "Nice" tick positions covering [from, to]: 1, 2, 2.5 or 5 times a power of ten.
 * @param {number} from @param {number} to @param {number} maxTicks
 * @returns {number[]}
 */
export function niceTicks(from, to, maxTicks = 6) {
  const span = Math.abs(to - from);
  if (!(span > 0) || !Number.isFinite(span)) return [from];
  const rough = span/Math.max(2, maxTicks);
  const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m*magnitude).find((s) => s >= rough) || 10*magnitude;
  const low = Math.min(from, to);
  const high = Math.max(from, to);
  const ticks = [];
  for (let value = Math.ceil(low/step)*step; value <= high + step*1e-6; value += step) {
    ticks.push(Math.abs(value) < step*1e-6 ? 0 : value);
  }
  return ticks;
}

/** @param {number} value @param {number} step */
function formatTick(value, step) {
  const decimals = step >= 10 ? 0 : step >= 1 ? 0 : step >= 0.1 ? 1 : 2;
  return value.toFixed(decimals);
}

/**
 * The rectangle the data is drawn in, i.e. the element minus the axis margins.
 * @param {number} width @param {number} height
 */
export function plotRect(width, height) {
  return {
    x: AXIS_MARGIN.left,
    y: AXIS_MARGIN.top,
    width: Math.max(1, width - AXIS_MARGIN.left - AXIS_MARGIN.right),
    height: Math.max(1, height - AXIS_MARGIN.top - AXIS_MARGIN.bottom),
  };
}

/**
 * The largest rectangle with the given aspect ratio (width/height) that fits in `rect`, centred in it:
 * an image keeps its proportions when the display is resized.
 * @param {{x: number, y: number, width: number, height: number}} rect
 * @param {number} aspect width/height; a non-positive or non-finite value: `rect` as it is
 */
export function fitAspect(rect, aspect) {
  if (!(aspect > 0) || !Number.isFinite(aspect)) return rect;
  let width = rect.width;
  let height = width/aspect;
  if (height > rect.height) {
    height = rect.height;
    width = height*aspect;
  }
  return {
    x: rect.x + (rect.width - width)/2,
    y: rect.y + (rect.height - height)/2,
    width: Math.max(1, width),
    height: Math.max(1, height),
  };
}

/**
 * Draws the axes around `rect`: a frame, ticks with labels and the axis names.
 *
 * @param {CanvasRenderingContext2D} context
 * @param {{x: number, y: number, width: number, height: number}} rect
 * @param {{x: [number, number], y: [number, number], xLabel?: string, yLabel?: string,
 *          title?: string}} axes ranges in the units the labels announce
 */
export function drawAxes(context, rect, axes) {
  const { x: xRange, y: yRange } = axes;
  context.save();
  context.font = FONT;
  context.strokeStyle = AXIS_COLOUR;
  context.fillStyle = LABEL_COLOUR;
  context.lineWidth = 1;

  // The plotting area's frame.
  context.strokeRect(rect.x + 0.5, rect.y + 0.5, rect.width, rect.height);

  const xTicks = niceTicks(xRange[0], xRange[1]);
  const xStep = xTicks.length > 1 ? Math.abs(xTicks[1] - xTicks[0]) : 1;
  context.textAlign = "center";
  context.textBaseline = "top";
  for (const tick of xTicks) {
    const position = rect.x + ((tick - xRange[0])/(xRange[1] - xRange[0]))*rect.width;
    if (position < rect.x - 1 || position > rect.x + rect.width + 1) continue;
    context.beginPath();
    context.moveTo(position, rect.y + rect.height);
    context.lineTo(position, rect.y + rect.height + 5);
    context.stroke();
    context.fillText(formatTick(tick, xStep), position, rect.y + rect.height + 8);
  }

  const yTicks = niceTicks(yRange[0], yRange[1]);
  const yStep = yTicks.length > 1 ? Math.abs(yTicks[1] - yTicks[0]) : 1;
  context.textAlign = "right";
  context.textBaseline = "middle";
  for (const tick of yTicks) {
    const position = rect.y + ((tick - yRange[0])/(yRange[1] - yRange[0]))*rect.height;
    if (position < rect.y - 1 || position > rect.y + rect.height + 1) continue;
    context.beginPath();
    context.moveTo(rect.x - 5, position);
    context.lineTo(rect.x, position);
    context.stroke();
    context.fillText(formatTick(tick, yStep), rect.x - 8, position);
  }

  if (axes.xLabel) {
    context.textAlign = "center";
    context.textBaseline = "bottom";
    context.fillText(axes.xLabel, rect.x + rect.width/2, rect.y + rect.height + AXIS_MARGIN.bottom - 4);
  }
  if (axes.yLabel) {
    context.save();
    context.translate(12, rect.y + rect.height/2);
    context.rotate(-Math.PI/2);
    context.textAlign = "center";
    context.textBaseline = "top";
    context.fillText(axes.yLabel, 0, 0);
    context.restore();
  }
  if (axes.title) {
    context.textAlign = "left";
    context.textBaseline = "alphabetic";
    context.fillStyle = "#f0f2f5";
    context.fillText(axes.title, rect.x, rect.y - 8);
  }
  context.restore();
}
