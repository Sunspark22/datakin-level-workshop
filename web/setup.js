const button = document.getElementById('supportCheck');
const status = document.getElementById('supportStatus');
button.addEventListener('click', async () => {
  button.disabled = true;
  status.textContent = 'Checking for a verified compatibility profile…';
  try {
    const response = await fetch('/api/support', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Editor-Token': button.dataset.token},
      body: '{}'
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'The support check failed.');
    status.textContent = result.message;
    document.getElementById('openWorkshop').focus();
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
