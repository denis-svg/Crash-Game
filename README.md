# Crash-Game

## Application Suitability

In a crash gamble game, different parts of the system can experience varying levels of traffic depending on events like peak gaming hours, promotions, or special tournaments. By using a microservices architecture, individual high-traffic components, such as the matchmaking service or lobby management, can be scaled independently, ensuring optimal performance without impacting other parts of the system.

Microservices also facilitate independent development, allowing teams to work on distinct features without causing disruptions. For example, the crash game’s lobby system can be maintained by a dedicated team that can deploy updates, introduce new game modes, or address bugs without affecting other critical services, such as the payment gateway or real-time gameplay engine. This allows for faster iterations and continuous improvement, ensuring a smooth user experience.

## Service Boundaries
![arhitecture](https://github.com/user-attachments/assets/cac8578b-bcc6-47d5-bef7-f5264aa24838)

## Data Management

- Service A

POST /user/auth/register
```json
{
  "userId": "user123",
  "username": "johnDoe",
  "email": "johndoe@example.com",
  "status": "registered"
}
```

POST /user/auth/login
```json
{
  "userId": "user123",
  "token": "eyJhbGciOiJIUzI1NiIsInR...",
  "status": "authenticated"
}
```

POST /user/auth/validate

GET /user/{userId}/balance
```json
{
  "userId": "user123",
  "balance": 1000
}
```

POST /user/{userId}/balance
```json
{
  "userId": "user123",
  "newBalance": 900
}
```

GET /user/{userId}/profile
```json
{
  "userId": "user123",
  "username": "johnDoe",
  "email": "johndoe@example.com"
}
```

- Service B

POST /game/lobby/create
```json
{
  "lobbyId": "lobby123",
  "lobbyName": "HighStakes",
  "maxPlayers": 10,
  "status": "created"
}
```

GET /game/lobbies
```json
[
  {
    "lobbyId": "lobby123",
    "lobbyName": "HighStakes",
    "currentPlayers": 5,
    "maxPlayers": 10
  },
  {
    "lobbyId": "lobby456",
    "lobbyName": "LowStakes",
    "currentPlayers": 2,
    "maxPlayers": 5
  }
]
```

POST /game/lobby/join
```json
{
  "lobbyId": "lobby123",
  "userId": "user123",
  "status": "joined"

```

POST /game/lobby/leave

POST /game/start
```json
{
  "lobbyId": "lobby123",
  "gameId": "game789",
  "status": "started"
}
```

GET /game/status/{gameId}
```json
{
  "gameId": "game789",
  "lobbyId": "lobby123",
  "currentMultiplier": 2.5,
  "status": "in-progress"
}
```
POST /game/bet
```
{
  "gameId": "game789",
  "userId": "user123",
  "betAmount": 100,
  "status": "bet placed"
}
```

POST /game/cashout
```
{
  "gameId": "game789",
  "userId": "user123",
  "multiplier": 3.2,
  "payout": 320,
  "status": "cashed out"
}
```

* WebSocket Connection: /game/ws/{lobbyId}
   * Description: Provides real-time game updates via WebSocket connection for users in a lobby.

