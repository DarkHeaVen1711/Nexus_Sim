// Phase 10 (TR-DASH-04): PDF export helper. Generating the report as a minimal
// standalone HTML document and opening it in a new window that auto-invokes the
// browser's print dialog is the standard "Save as PDF" path here — it keeps the
// bundle free of heavyweight PDF libraries and works offline.
export function openPrintWindow(html: string): void {
  const w = window.open('', '_blank', 'width=980,height=740');
  if (!w) return;
  w.document.open();
  w.document.write(html);
  w.document.close();
  w.focus();
  // Give the browser a moment to lay out before the print dialog opens.
  setTimeout(() => { w.print(); }, 350);
}