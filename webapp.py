import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
import requests

def get_header():
    token = os.environ.get('GH_TOKEN')
    return {'Authorization': 'token {}'.format(token)}

def get_pr_last_commit(id):
    url = "https://api.github.com/repos/isuruf/sympy/pulls/{}/commits".format(id)
    obj = requests.get(url, headers=get_header()).json()
    return obj[-1]["sha"]

def add_failure_status(sha, commenter):
    url = 'https://api.github.com/repos/isuruf/sympy/statuses/{}'.format(sha)
    payload = {
        "state":"failure",
        "target_url":"",
        "description":"{} says it's author's turn".format(commenter),
        "context":"continuous-integration/sympy-pr"
    }
    return requests.post(url, json=payload, headers=get_header())

def add_label(id, label):
    url = 'https://api.github.com/repos/isuruf/sympy/issues/{}/labels'.format(id)
    return requests.post(url, json=[label], headers=get_header())

def remove_label(id, label):
    url = 'https://api.github.com/repos/isuruf/sympy/issues/{}/labels/{}'.format(id, label)
    return requests.delete(url, headers=get_header())

def check_label(id, label):
    url = "https://api.github.com/repos/isuruf/sympy/issues/{}/labels".format(id)
    obj = requests.get(url, headers=get_header()).json()
    for l in obj:
        if l['name'] == label:
            return True
    return False

def author_turn(id):
    if not check_label(id, "PR: author's turn"):
        add_label(id, "PR: author's turn")
    remove_label(id, "PR: sympy's turn")

def sympy_turn(id):
    if not check_label(id, "PR: sympy's turn"):
        add_label(id, "PR: sympy's turn")
    remove_label(id, "PR: author's turn")

def add_success_status(sha, commenter):
    url = 'https://api.github.com/repos/isuruf/sympy/statuses/{}'.format(sha)
    payload = {
        "state":"success",
        "target_url":"",
        "description":"{} signed off".format(commenter),
        "context":"continuous-integration/sympy-pr"
    }
    return requests.post(url, json=payload, headers=get_header())

review = ['sign off', 'lgtm', '+1 to merge', '+1 for merge', '+1 for merging', 'needs review']
more_work = ['needs more work', 'need more work', '-1 to merge']

class MainHandler(tornado.web.RequestHandler):
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        if event == 'ping':
            self.write('pong')
        elif event == 'issue_comment':
            body = tornado.escape.json_decode(self.request.body)
            pr = int(body['issue']['number'])
            comment = body['comment']['body']
            commenter = body['comment']['user']['login']

            if (comment.lower() in more_work):
                #commit_id = get_pr_last_commit(int(pr))
                #add_failure_status(commit_id, commenter)
                author_turn(pr)
            elif (comment.lower() in review):
                #commit_id = get_pr_last_commit(int(pr))
                #add_success_status(commit_id, commenter)
                sympy_turn(pr)
        elif event == 'pull_request':
            body = tornado.escape.json_decode(self.request.body)
            action = body['action']
            title = body['pull_request']['title']
            pr = int(body['pull_request']['number'])
            if 'WIP' in title:
                author_turn(pr)
                return
            if action == "opened" or action == "synchronize":
                sympy_turn(pr)
        else:
            print('Unhandled event "{}".'.format(event))
            self.set_status(404)
            self.write_error(404)

def main():
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    port = int(os.environ.get("PORT", 5000))
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
