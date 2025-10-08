const getPlatform = () => {
  if (window.Capacitor?.isNativePlatform()) return 'native';
  else return 'web';
};

const isBannerDismissed = async (bannerId) => {
  if (window.Capacitor?.isNativePlatform()) {
    // TODO: Re-neable once support for dismissBanner is implemented
    return true;
  } else {
    let dismissed = window.sessionStorage.getItem('dismissed');
    dismissed = dismissed ? dismissed.split(',') : [];
    return dismissed.includes(bannerId);
  }
};

const dismissBanner = async (bannerId) => {
  if (window.Capacitor?.isNativePlatform()) {
    // TODO: Dismiss banner on native
  } else {
    let dismissed = window.sessionStorage.getItem('dismissed');
    dismissed = dismissed ? dismissed.split(',') : [];
    dismissed.push(bannerId);
    window.sessionStorage.setItem('dismissed', dismissed?.join(','));
  }
};

const refreshBanner = (bId) => {
  const platform = getPlatform();
  const params = [`platform=${platform}`];
  if (bId) params.push(`bannerId=${bId}`);

  let path = `/banner?${params.join('&')}`;

  const handleResponse = async (data) => {
    if (!data.h) return;

    if (await isBannerDismissed(data.id)) {
      return;
    }

    const node = document.getElementById('page-banner');
    const paddingNode = document.querySelector('.bpadding');

    node.style.backgroundColor = data.bgc;
    node.style.color = data.c;
    node.innerHTML = data.h;

    const aNodes = node.getElementsByTagName('a');
    for (const an of aNodes) an.style.color = data.ac;

    node.getElementsByClassName('bclose')[0].addEventListener('click', () => {
      node.classList.remove('open');
      if (paddingNode) paddingNode.classList.remove('open');
      if (data.id && !bId) {
        dismissBanner(data.id);
      }
    });

    node.classList.add('open');
    if (paddingNode) paddingNode.classList.add('open');
  };

  if (window.Capacitor?.isNativePlatform()) {
    window.yoyoNative
      ?.apiRequest({
        path,
        method: 'GET',
      })
      .then((res) => res.data)
      .then((data) => {
        if (data.status === 200 && data.json) {
          handleResponse(JSON.parse(data.json));
        }
      });
  } else {
    fetch(`${window.yoyoData.config.API_PATH}${path}`)
      .then((res) => res.json())
      .then((data) => handleResponse(data));
  }
};

window.onload = async function () {
  setTimeout(
    () =>
      document.addEventListener(
        'scroll',
        () => {
          let p = new URLSearchParams(document.location.search);
          let bId = p.get('bannerId');

          refreshBanner(bId);
        },
        { once: true },
      ),
    2000,
  );
};
