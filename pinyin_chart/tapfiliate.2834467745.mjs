const paramsString = window.location.search;
const searchParams = new URLSearchParams(paramsString);

if (searchParams.has('ref')) {
  fetch(`/createref${window.location.search}`);
}
