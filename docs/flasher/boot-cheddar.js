/* Remplace uniquement la tâche d'animation dans une image Supermodel 3.06 vérifiée. */
(function () {
"use strict";
const B = typeof module === "object" ? require("./builder.js") : window.MCBuilder;
const base = 0x40000400, task = 0x40053a6c, end = 0x40053e74;
const titles = new Set([
  "6669c780244b0f21256a418dcf8871b83ee8b9e9b84deb3a26aa2835d044c97a", // Full
  "63298fa8a09a2c22bf536f7beddc7731ef11afd8805625dc36f3d5b6886f9733", // Lite
]);
const sha = bytes => B.hex(B.sha256(bytes));

function apply(source, codeHex) {
  const transport = B.unwrap(source), image = B.parseContainer(transport.stream);
  const section = s => image.blob.subarray(s.off, s.off + s.size);
  const main = image.sections.find(s => s.id === 3);
  const { data, ops } = B.aplibDepack(section(main), { bootLayout: true });
  const offset = task - base, limit = end - base;
  const code = B.fromHex(codeHex);
  if (!code.length || code.length > limit - offset ||
      B.hex(data.subarray(0x40053a2e - base, 0x40053a32 - base)) !== "487a003c" ||
      !titles.has(sha(data.subarray(offset, limit)))) {
    throw new Error("Cheddar Butt needs a compatible Supermodel 3.06 boot task");
  }

  // Le chargeur lean pourrait recouvrir les octets natifs après décompression.
  const header = 0x401aa140 - base;
  if (B.hex(data.subarray(header, header + 8)) !== "534d434c45414e31") {
    throw new Error("Cheddar Butt needs the Supermodel 3.06 lean layout");
  }
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const payload = view.getUint32(header + 28) - base;
  const records = view.getUint32(payload);
  for (let i = 0; i < records; i++) {
    const record = payload + 4 + i * 12;
    const at = view.getUint32(record), bytes = view.getUint32(record + 4) & 0x7fffffff;
    if (at < end && at + bytes > 0x40053a2e) throw new Error("Boot task overlaps a firmware segment");
  }

  const dirty = new Uint8Array(data.length);
  for (let i = 0; i < code.length; i++) dirty[offset + i] = +(data[offset + i] !== code[i]);
  data.set(code, offset);
  const packed = B.aplibRepack(data, ops, dirty);
  const mainOsSha = sha(data);
  if (sha(B.aplibDepack(packed, { bootLayout: true }).data) !== mainOsSha) {
    throw new Error("Cheddar Butt MAIN packing mismatch");
  }
  const digest = image.blob.length - 32;
  const plains = image.sections.map(s => {
    try { return s === main ? data : B.aplibDepack(section(s)).data; }
    catch { return new Uint8Array(); }
  });
  const key = B.findKey(plains, image.blob.subarray(0, digest), image.blob.subarray(digest));
  if (!key) throw new Error("Firmware signature key not found");
  const blob = B.rebuildContainer(image, { 3: packed }, key);
  if (blob.length > 0x1c0000) throw new Error("Cheddar Butt firmware exceeds flash capacity");
  const raw = B.wrap(B.buildStream(blob, 101), transport.product, transport.start_seq);
  return { raw, mainOsSha };
}

if (typeof module === "object") module.exports = { apply };
else window.MCBootCheddar = { apply };
})();
