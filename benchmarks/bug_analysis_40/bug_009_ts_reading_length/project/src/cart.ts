export function totalCount(cart?: { items?: string[] }) {
  return cart.items.length;
}
