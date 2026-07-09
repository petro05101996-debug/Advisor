package app;
class OrderService {
  String customerName(Order order) {
    return order.getCustomer().getName();
  }
}
