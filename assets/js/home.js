/* The rankings and summaries are rendered by Jekyll from the latest published
 * tables. JavaScript only changes audience display; it never reorders ranks. */
document.querySelectorAll('[data-number]').forEach(el => {
  const value = Number(el.textContent);
  if (Number.isFinite(value)) el.textContent = value.toLocaleString('ko-KR');
});
document.querySelectorAll('[data-mode]').forEach(button => {
  button.addEventListener('click', () => {
    const mode = button.dataset.mode;
    document.querySelectorAll('[data-mode]').forEach(other => {
      other.classList.toggle('active', other === button);
      other.setAttribute('aria-pressed', String(other === button));
    });
    document.querySelectorAll('.count[data-daily]').forEach(count => {
      const value = mode === 'total' ? count.dataset.total : count.dataset.daily;
      count.replaceChildren(document.createTextNode(value));
      const unit = document.createElement('small');
      unit.textContent = ' 명';
      count.append(unit);
    });
    document.getElementById('audience-heading').textContent = mode === 'total' ? '누적 관객수' : '일일 관객수';
  });
});
