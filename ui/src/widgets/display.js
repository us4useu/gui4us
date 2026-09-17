// @ts-check
/** anywidget entry point for <g4u-stream-view> (see gui4us/view/jupyter/widgets.py). */
import "../components/stream-view.js";
import { widgetFor } from "./_widget.js";

export default widgetFor("g4u-stream-view", (element, model) => {
  // The Python widget picks which display it shows.
  const displayId = model.get("display_id");
  if (displayId) element.setAttribute("display", displayId);
  element.style.minHeight = `${model.get("height") || 320}px`;
});
