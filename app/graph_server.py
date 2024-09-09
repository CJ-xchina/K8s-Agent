import json
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bean.graph.Graph import Graph

# uvicorn app.graph_server:app --reload
app = FastAPI()

# 配置 CORS
origins = [
    "http://localhost:3000",  # 允许前端 Vue 应用的地址
    "http://localhost:8080",  # Vue 其他可能的端口
    "http://127.0.0.1:3000",  # 允许同样的地址但用 IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic 使用的模型
class Endpoint(BaseModel):
    id: str
    orientation: List[int]


class NodeResponse(BaseModel):
    nodeId: str
    question: str
    regex: Optional[str]
    action: Optional[str]
    conclusion: Optional[str]
    description: Optional[str]
    nodeType: str
    nodeLeft: int
    nodeTop: int
    endpoints: List[Endpoint]
    reachableNodes: List[str]
    conditions: List[str]


class EdgeResponse(BaseModel):
    sourceNode: str
    targetNode: str
    type: str
    condition: Optional[str]


class GraphResponse(BaseModel):
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]


# 初始化全局图对象
graph : Graph = None


@app.post("/upload-json/")
async def upload_file(file: UploadFile = File(...)):
    global graph
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")

    contents = await file.read()
    try:
        json_data = json.loads(contents)
        graph = Graph(start_node_id="A", json_source=json_data)
        return {"message": "Graph successfully uploaded and initialized"}  # 返回200 OK
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing graph: {str(e)}")


@app.get("/graph")
def get_graph_data():
    """
    获取整个图的结构，包含节点和边。
    """
    if graph is None:
        raise HTTPException(status_code=400, detail="No graph has been uploaded yet")
    return graph



@app.get("/node/{node_id}", response_model=NodeResponse)
def get_node_data(node_id: str):
    """
    根据节点ID获取指定节点的数据。
    :param node_id: 节点ID。
    :return: 节点数据。
    """
    if graph is None:
        raise HTTPException(status_code=400, detail="No graph has been uploaded yet")

    node = graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node with id {node_id} not found")

    return node.to_dict()


@app.get("/reachable_nodes/{node_id}", response_model=List[str])
def get_reachable_nodes(node_id: str):
    """
    获取指定节点ID的可达节点。
    :param node_id: 节点ID。
    :return: 可达节点ID的列表。
    """
    if graph is None:
        raise HTTPException(status_code=400, detail="No graph has been uploaded yet")

    return graph.get_reachable_nodes(node_id)


@app.get("/isolated_nodes", response_model=List[str])
def get_isolated_nodes():
    """
    查找图中的孤立节点。
    :return: 孤立节点ID的列表。
    """
    if graph is None:
        raise HTTPException(status_code=400, detail="No graph has been uploaded yet")

    return graph.find_isolated_nodes()


@app.get("/is_terminal/{node_id}", response_model=bool)
def is_terminal_node(node_id: str):
    """
    检查给定节点是否为终止节点。
    :param node_id: 节点ID。
    :return: 如果是终止节点返回True，否则返回False。
    """
    if graph is None:
        raise HTTPException(status_code=400, detail="No graph has been uploaded yet")

    return graph.is_terminal_node(node_id)
