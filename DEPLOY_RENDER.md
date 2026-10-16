# Deploy ChronosMatch API on Render

This API loads the Cython `MatchingEngine` from `matching_engine.pyx`. Render builds a Linux-native extension from source; the Windows `.pyd` file is not used.

## Deploy

1. In Render, choose **New + → Blueprint**.
2. Connect the GitHub repository `pratulbadhautiya/ChronosMatch`.
3. Select branch `pratul` (the branch containing `matching_engine.pyx` and `setup.py`).
4. Render should detect `render.yaml`; review the service and create it.
5. Wait for the Docker build to finish, then open the service URL and check `/health`.

## API

- `GET /` — service info
- `GET /health` — health check
- `GET /api/stats` — matching-engine statistics
- `GET /api/orderbook` — resting orders and statistics
- `POST /api/orders` — submit an order

Example JSON:

```json
{
  "side": "BUY",
  "price": 100,
  "quantity": 5
}
```

Price is represented as a positive integer in the engine's price units. The API uses one in-memory engine instance; orders reset when the service restarts and are not shared across multiple instances. This is a simulator, not a connection to a real exchange.

Interactive API docs are available at `/docs` on the deployed service.
