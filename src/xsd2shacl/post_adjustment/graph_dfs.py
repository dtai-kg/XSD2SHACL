from collections import defaultdict

class GrapDFS:
    def __init__(self):
        self.graph = defaultdict(list)

    def add_edge(self, u, v):
        self.graph[u].append(v)

    def dfs(self, node, visited, path, paths):
        visited[node] = True
        path.append(node)
        
        if node not in self.graph:
            paths[node].append(path.copy())
        else:
            for neighbor in self.graph[node]:
                if not visited[neighbor]:
                    self.dfs(neighbor, visited, path, paths)
        
        path.pop()
        visited[node] = False

    def find_paths(self):
        visited = defaultdict(bool)
        paths = defaultdict(list)

        for node in self.graph.keys():
            self.dfs(node, visited, [], paths)

        return paths