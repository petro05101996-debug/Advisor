export function renderProfile(user) {
  return `<a href="/users/${user.id}">${user.name}</a>`;
}
