from flask import Flask
from flask import request
from flask import render_template
import datetime
import pymongo
from bson.objectid import ObjectId
con = pymongo.MongoClient('localhost')
db = con.testing
global nodes
import json

app = Flask(__name__)


class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime.datetime):
            return str(o)
        return JSONEncoder.default(self, o)

def dumps(obj):
    return MyEncoder().encode(obj)

def get_project_id(project):
    res = db.projects.find_one({'name':project})
    if not res:
        return None
    return res['_id']

@app.route('/<project>/node')
def make_node(project):
    node = dict(request.args)
    res = db.nodes.find_one(node)
    if not res:
        db.nodes.insert(node)
        res = node
    return dumps(res)

@app.route('/<project>/link')
def link_nodes(project):
    src = ObjectId(request.args['src'])
    dst = ObjectId(request.args['dst'])
    time = datetime.datetime.now()
    search = {'source':src,
              'target':dst,
              'project':get_project_id(project)}
    if 'desc' in request.args:
        search['desc'] = request.args.get('desc')

    upsert = search.copy()
    upsert['visited'] = [time]

    res = db.links.find_and_modify(search, 
            update={'$push':{'visited':time}},
            upsert=upsert,
            new=True)

    return dumps(res)

@app.route('/<project>/start')
def start_project(project):
    if get_project_id(project):
        raise Exception("Project allready exists")

    project = {'name':project}

    project['description'] = request.args.get('description') or ""
    db.projects.insert(project)

    return render_template('project.html', project=project)

@app.route('/<project>.json')
def get_project_json(project):
    project_id = get_project_id(project)

    links = list(db.links.find({'project':project_id}))
    nodes = {}
    def get_node(_id):
        if not _id in nodes:
            n_id = len(nodes)
            nodes[_id] = {'id':n_id,
                          'name':str(_id),
                          'weight':0,
                          'group':1}
        return nodes[_id]
    for l in links:
        l['source'] = get_node(l['source'])['id']
        dst = get_node(l['target'])
        dst['weight'] += len(l['visited'])
        l['target'] = dst['id']
        l['value'] = len(l['visited'])
        del l['project']
        del l['visited']

    nodes = nodes.values()
    nodes.sort(lambda x,y: cmp(x['id'], y['id']))
    return dumps({'nodes':nodes, 'links':links})

@app.route('/<project>')
def project_graph(project):
    project = {'name':project}
    project = db.projects.find_one(project)

    return render_template('graph.html', project=project)

if __name__ == '__main__':
    app.run(debug=True)