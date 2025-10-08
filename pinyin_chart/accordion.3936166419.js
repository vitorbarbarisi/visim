var accordion = document.getElementsByClassName('accordion-more-component')[0];
accordion.addEventListener(
  'click',
  function (e) {
    var targetClass = e.target.className || e.target.parentNode.className;
    console.log(targetClass);
    if (
      targetClass
        .split(' ')
        .some((name) => name == 'item_header' || name == 'btn-arrows')
    ) {
      var accordionItem = getParent(e.target, 'accordion-item');
      var className = accordionItem.className;
      if (className.indexOf('open') > -1)
        accordionItem.classList.remove('open');
      else accordionItem.classList.add('open');
    } else if (targetClass.indexOf('btn-more') > -1) {
      var isAll = accordion.className.indexOf('is-all') > -1;
      var strongEl =
        e.target.tagName == 'STRONG'
          ? e.target
          : e.target.parentNode.getElementsByTagName('strong')[0];
      console.log(strongEl);
      if (isAll) {
        strongEl.innerText = 'More';
        accordion.classList.remove('is-all');
      } else {
        strongEl.innerText = 'Less';
        accordion.classList.add('is-all');
      }
      e.target.blur();
      e.target.parentNode.blur();
    }
  },
  true,
);

function getParent(node, name) {
  if (node.className && node.className.indexOf(name) > -1) return node;
  else return getParent(node.parentNode, name);
}
