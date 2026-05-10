"""
GraphQL client for communicating with the TS layer's GraphQL server.

Provides methods for:
- createVirtualFile(name, content, source, ttl, createdBy)
- dropVirtualFile(name)
- setVirtualFileContext(name, inContext)
- getVirtualFiles(inContext)
- getVirtualFile(name)
- sendChatMessage(content, agentName, subjectId)
- getChatMessages(subjectId)
- queryGraph(query, target, depth, scope)
- connectWebSocket(maxRetries, baseDelayMs) – WebSocket streaming with retry
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests


class GraphQLClient:
    """Client for the TS layer's GraphQL server over HTTP and WebSocket."""

    def __init__(self, endpoint: Optional[str] = None, ws_endpoint: Optional[str] = None, verify_ssl: bool = True):
        self.endpoint = endpoint or os.environ.get(
            "GRAPHIQL_ENDPOINT", "http://host.docker.internal:3000/graphql"
        )
        self.ws_endpoint = ws_endpoint or os.environ.get(
            "WS_ENDPOINT", "ws://host.docker.internal:3000/~/ws"
        )
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.ws = None
        self.ws_connected = False
        self.ws_subscriptions = {}

    def _execute(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query and return the result."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = self.session.post(
                self.endpoint,
                json=payload,
                verify=self.verify_ssl,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            if "errors" in result:
                raise RuntimeError(f"GraphQL errors: {result['errors']}")
            return result.get("data", {})
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"GraphQL request failed: {e}")

    # ------------------------------------------------------------------ #
    # Virtual File Operations                                            #
    # ------------------------------------------------------------------ #

    def create_virtual_file(
        self,
        name: str,
        content: str,
        source: str,
        ttl: Optional[int] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a virtual file in the graph."""
        mutation = """
        mutation CreateVirtualFile($name: String!, $content: String!, $source: String!, $ttl: Int, $createdBy: String!) {
            createVirtualFile(name: $name, content: $content, source: $source, ttl: $ttl, createdBy: $createdBy) {
                id
                name
                tokens
                expiresAt
                inContext
            }
        }
        """
        variables = {
            "name": name,
            "content": content,
            "source": source,
            "ttl": ttl,
            "createdBy": created_by or "aider",
        }
        data = self._execute(mutation, variables)
        return data.get("createVirtualFile", {})

    def drop_virtual_file(self, name: str) -> bool:
        """Drop a virtual file from the graph."""
        mutation = """
        mutation DropVirtualFile($name: String!) {
            dropVirtualFile(name: $name)
        }
        """
        data = self._execute(mutation, {"name": name})
        return data.get("dropVirtualFile", False)

    def set_virtual_file_context(self, name: str, in_context: bool) -> Dict[str, Any]:
        """Set whether a virtual file is included in aider's context."""
        mutation = """
        mutation SetVirtualFileContext($name: String!, $inContext: Boolean!) {
            setVirtualFileContext(name: $name, inContext: $inContext) {
                name
                inContext
            }
        }
        """
        data = self._execute(mutation, {"name": name, "inContext": in_context})
        return data.get("setVirtualFileContext", {})

    def get_virtual_files(self, in_context: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get virtual files, optionally filtered by context status."""
        query = """
        query GetVirtualFiles($inContext: Boolean) {
            virtualFiles(inContext: $inContext) {
                id
                name
                content
                tokens
                source
                createdAt
                expiresAt
                inContext
                createdBy
            }
        }
        """
        variables = {}
        if in_context is not None:
            variables["inContext"] = in_context
        data = self._execute(query, variables)
        return data.get("virtualFiles", [])

    def get_virtual_file(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single virtual file by name."""
        query = """
        query GetVirtualFile($name: String!) {
            virtualFile(name: $name) {
                id
                name
                content
                tokens
                source
                createdAt
                expiresAt
                inContext
                createdBy
            }
        }
        """
        data = self._execute(query, {"name": name})
        return data.get("virtualFile")

    # ------------------------------------------------------------------ #
    # Chat Operations                                                     #
    # ------------------------------------------------------------------ #

    def send_chat_message(
        self,
        content: str,
        agent_name: str,
        subject_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a chat message via GraphQL."""
        mutation = """
        mutation SendChatMessage($content: String!, $agentName: String!, $subjectId: String) {
            sendChatMessage(content: $content, agentName: $agentName, subjectId: $subjectId) {
                id
                content
                agentName
                subjectId
                timestamp
            }
        }
        """
        variables = {
            "content": content,
            "agentName": agent_name,
        }
        if subject_id:
            variables["subjectId"] = subject_id
        data = self._execute(mutation, variables)
        return data.get("sendChatMessage", {})

    def get_chat_messages(self, subject_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get chat messages, optionally filtered by subject."""
        query = """
        query GetChatMessages($subjectId: String) {
            chatMessages(subjectId: $subjectId) {
                id
                content
                agentName
                subjectId
                timestamp
            }
        }
        """
        variables = {}
        if subject_id:
            variables["subjectId"] = subject_id
        data = self._execute(query, variables)
        return data.get("chatMessages", [])

    # ------------------------------------------------------------------ #
    # Graph Query Operations                                              #
    # ------------------------------------------------------------------ #

    def query_graph(
        self,
        query_type: str,
        target: str,
        depth: Optional[int] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query the graph for definitions, references, related files, etc."""
        graph_query = """
        query GraphQuery($query: String!, $target: String!, $depth: Int, $scope: GraphQueryScope) {
            graphQuery(query: $query, target: $target, depth: $depth, scope: $scope) {
                result
            }
        }
        """
        variables = {
            "query": query_type,
            "target": target,
        }
        if depth is not None:
            variables["depth"] = depth
        if scope:
            variables["scope"] = scope
        data = self._execute(graph_query, variables)
        return data.get("graphQuery", {})

    def find_definitions(self, target: str) -> Dict[str, Any]:
        """Find definitions for a given target symbol."""
        return self.query_graph("find_definitions", target)

    def find_references(self, target: str) -> Dict[str, Any]:
        """Find references for a given target symbol."""
        return self.query_graph("find_references", target)

    def find_related_files(self, target: str) -> Dict[str, Any]:
        """Find files related to a given target."""
        return self.query_graph("find_related_files", target)

    def find_agents(self, target: Optional[str] = None) -> Dict[str, Any]:
        """Find agents, optionally filtered by target."""
        return self.query_graph("find_agents", target or "")

    def find_tasks(self, target: Optional[str] = None) -> Dict[str, Any]:
        """Find tasks, optionally filtered by target."""
        return self.query_graph("find_tasks", target or "")

    def get_file_context(self, target: str, line_start: Optional[int] = None, line_end: Optional[int] = None) -> Dict[str, Any]:
        """Get context for a file, optionally for a specific line range."""
        scope = {}
        if line_start is not None:
            scope["lineStart"] = line_start
        if line_end is not None:
            scope["lineEnd"] = line_end
        return self.query_graph("get_file_context", target, scope=scope if scope else None)

    # ------------------------------------------------------------------ #
    # WebSocket Streaming Methods                                        #
    # ------------------------------------------------------------------ #

    def connect_websocket(self, max_retries: int = 5, base_delay_ms: int = 1000) -> None:
        """
        Connect to the WebSocket streaming endpoint.
        Retries with exponential backoff if the connection fails.
        Falls back to HTTP polling if all attempts fail.
        """
        import websocket

        attempt = 0
        while attempt <= max_retries:
            try:
                if attempt > 0:
                    delay = base_delay_ms * (2 ** (attempt - 1)) / 1000.0
                    print(f"[GraphQLClient] WebSocket connection attempt {attempt}/{max_retries}, waiting {delay}s...")
                    time.sleep(delay)

                self.ws = websocket.WebSocketApp(
                    self.ws_endpoint,
                    on_open=self._on_ws_open,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close,
                )
                # Run in a background thread
                import threading
                self._ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
                self._ws_thread.start()

                # Wait briefly for connection to establish
                time.sleep(0.5)
                if self.ws_connected:
                    print("[GraphQLClient] WebSocket connected")
                    return
                else:
                    # Close and retry
                    self.ws.close()
                    self.ws = None
                    attempt += 1

            except Exception as e:
                print(f"[GraphQLClient] WebSocket connection attempt {attempt} failed: {e}")
                self.ws_connected = False
                attempt += 1

        print("[GraphQLClient] All WebSocket connection attempts failed, falling back to HTTP polling")
        self.ws_connected = False

    def disconnect_websocket(self) -> None:
        """Disconnect from the WebSocket streaming endpoint."""
        if self.ws:
            self.ws.close()
            self.ws = None
        self.ws_connected = False

    def subscribe(self, channel: str, callback) -> None:
        """Subscribe to a streaming channel."""
        if channel not in self.ws_subscriptions:
            self.ws_subscriptions[channel] = set()
        self.ws_subscriptions[channel].add(callback)

        if self.ws_connected and self.ws:
            self.ws.send(json.dumps({
                "type": "subscribe",
                "channels": [channel],
            }))

    def unsubscribe(self, channel: str, callback=None) -> None:
        """Unsubscribe from a streaming channel."""
        callbacks = self.ws_subscriptions.get(channel)
        if not callbacks:
            return

        if callback:
            callbacks.discard(callback)
            if not callbacks:
                del self.ws_subscriptions[channel]
        else:
            del self.ws_subscriptions[channel]

        if self.ws_connected and self.ws:
            self.ws.send(json.dumps({
                "type": "unsubscribe",
                "channels": [channel],
            }))

    def send_event(self, event: str, data: Any = None) -> None:
        """Send an event via WebSocket to be broadcast to other clients."""
        if self.ws_connected and self.ws:
            self.ws.send(json.dumps({
                "type": "event",
                "event": event,
                "data": data,
            }))

    def _on_ws_open(self, ws):
        """Handle WebSocket open event."""
        self.ws_connected = True
        print("[GraphQLClient] WebSocket connected")

    def _on_ws_message(self, ws, message):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            self._handle_ws_message(data)
        except json.JSONDecodeError:
            print(f"[GraphQLClient] Error parsing WebSocket message: {message}")

    def _on_ws_error(self, ws, error):
        """Handle WebSocket error event."""
        print(f"[GraphQLClient] WebSocket error: {error}")
        self.ws_connected = False

    def _on_ws_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close event."""
        print("[GraphQLClient] WebSocket disconnected")
        self.ws_connected = False

    def _handle_ws_message(self, message: dict):
        """Handle an incoming WebSocket message."""
        msg_type = message.get("type")

        if msg_type == "connected":
            print(f"[GraphQLClient] Connected with clientId: {message.get('clientId')}")

        elif msg_type == "subscribed":
            print(f"[GraphQLClient] Subscribed to channels: {', '.join(message.get('channels', []))}")

        elif msg_type == "unsubscribed":
            print(f"[GraphQLClient] Unsubscribed from channels: {', '.join(message.get('channels', []))}")

        elif msg_type == "event":
            self._handle_event(message.get("event"), message.get("data"))

        elif msg_type == "pong":
            pass  # Keepalive response

        elif msg_type == "error":
            print(f"[GraphQLClient] WebSocket error: {message.get('error', {}).get('message')}")

        else:
            print(f"[GraphQLClient] Unknown message type: {msg_type}")

    def _handle_event(self, event: str, data: Any):
        """Handle an event from a streaming channel."""
        callbacks = self.ws_subscriptions.get(event)
        if callbacks:
            for callback in callbacks:
                try:
                    callback(data)
                except Exception as e:
                    print(f"[GraphQLClient] Error in event callback for {event}: {e}")
