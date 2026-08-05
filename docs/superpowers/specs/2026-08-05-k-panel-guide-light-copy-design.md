# K-Panel Guide Light Theme and Copy Controls

## Goal

Make the published five-step participant guide easier to read in workshop environments and let participants copy command blocks without selecting text manually.

## Scope

- Restyle `docs/KPANEL_SETUP_EXECUTIVE.html` as an always-light page.
- Preserve the existing layout, five-step navigation, logos, responsive behavior, print support, and accessibility behavior.
- Add one copy control to every command card containing a `<pre><code>` block.
- Keep the guide standalone with no new libraries or network dependencies.

## Visual Design

The page uses a warm off-white canvas, white cards, dark navy text, muted slate supporting text, and pale blue/violet accents. Borders and shadows remain subtle so cards are distinct without recreating the current dark, glowing appearance. Success and troubleshooting callouts retain green and amber semantic colors with light backgrounds.

Command cards place their label and copy button in a compact header row. The button uses the same accent palette as the step controls, has a visible keyboard focus state, and is omitted from print output.

## Copy Interaction

On page load, JavaScript adds a `Copy` button to each `.command` element containing a `<pre><code>` block. Activating the button copies the code block's plain text exactly, preserving line breaks.

The primary path uses `navigator.clipboard.writeText`. If that API is unavailable or rejects, a temporary textarea and `document.execCommand("copy")` provide a fallback. The button displays `Copied` after success or `Copy failed` after failure, then returns to `Copy`. An `aria-live` region announces the result to assistive technology.

## Error Handling

Copy failures do not affect step navigation or other guide behavior. Temporary fallback elements are always removed. Repeated clicks clear the previous reset timer so feedback remains predictable.

## Testing

Automated structural tests will verify:

- the dark palette is replaced by light theme variables and surfaces;
- every command block receives an accessible copy control;
- the Clipboard API and fallback paths are present;
- success and failure feedback states are defined;
- copy controls are hidden in print mode;
- existing five-step navigation, reduced-motion behavior, and local image assets remain intact.

The published GitHub Pages artifact will also be fetched after deployment to confirm the light-theme and copy-control markup is live.
