function playSibling(sibling) {
  if (sibling?.tagName?.toLowerCase() === 'audio') {
    sibling.play();
  }
}

function handleDocumentClick(e) {
  if (e.target.tagName.toLowerCase() === 'img') {
    playSibling(e.target.nextSibling);
  } else if (e.target.classList.contains('audio-label')) {
    playSibling(e.target.previousSibling);
  }
}

document.addEventListener('mousedown', handleDocumentClick);
