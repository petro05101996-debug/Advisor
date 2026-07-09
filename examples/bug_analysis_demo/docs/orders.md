# Orders service

If CRM user is absent for an order, the service must return a domain NOT_FOUND error.
It must not leak TypeError/NullPointerException to the client.
