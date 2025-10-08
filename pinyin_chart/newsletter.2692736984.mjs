function showResult(success, description, inputSelector, btnSelector) {
  const inputElement = document.querySelector(inputSelector);
  if (inputElement) {
    inputElement.value = '';
  }

  document.querySelectorAll('.newsletter_notification').forEach((ele) => {
    const notification = document.createElement('p');
    notification.classList.add('newsletter_result');
    notification.textContent = description;
    notification.style.color = success ? '#63b768' : '#fc4b49';
    notification.style.fontWeight = '700';

    ele.innerHTML = '';
    ele.append(notification);
  });

  const btnElement = document.querySelector(btnSelector);
  if (btnElement) {
    btnElement.removeAttribute('disabled');
  }
}

function subNewsletter(inputSelector, btnSelector) {
  const inputElement = document.querySelector(inputSelector);
  const btnElement = document.querySelector(btnSelector);
  if (!inputElement) return;

  const email = inputElement.value;
  const url = '/api/v1/newsletter-signup';

  if (email) {
    if (btnElement) btnElement.setAttribute('disabled', '');

    // This should remove across all of them
    document
      .querySelectorAll('.newsletter_notification')
      .forEach((element) => (element.innerHTML = ''));

    fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        email,
      }),
    })
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          showResult(
            data.success,
            data.description,
            inputSelector,
            btnSelector,
          );
        } else {
          showResult(
            false,
            'Something went wrong.',
            inputSelector,
            btnSelector,
          );
        }
      })
      .catch((err) => {
        showResult(false, 'Something went wrong.', inputSelector, btnSelector);
        console.error(err);
      });
  }
}

// Footer form
const e1 = document.getElementById('btnSubscribe');
if (e1)
  e1.addEventListener('click', () =>
    subNewsletter('#input_email', '#btnSubscribe'),
  );

// Blog list form
const e2 = document.getElementById('btn_subNewletter');
if (e2)
  e2.addEventListener('click', () =>
    subNewsletter('#input_email1', '#btn_subNewletter'),
  );

const e3 = document.getElementById('newsletter_subscription_desc');
if (e3) e3.addEventListener('click', (e) => e.stopPropagation());
