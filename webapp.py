import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
import requests

def get_header():
    token = os.environ.get('GH_TOKEN')
    return {'Authorization': 'token {}'.format(token)}

def get_pr_last_commit(id):
    url = "https://api.github.com/repos/isuruf/symengine/pulls/{}/commits".format(id)
    obj = requests.get(url, headers=get_header()).json()
    return obj[-1]["sha"]

def add_failure_status(sha, commenter):
    url = 'https://api.github.com/repos/isuruf/symengine/statuses/{}'.format(sha)
    payload = {
        "state":"failure",
        "target_url":"",
        "description":"{} says it's author's turn".format(commenter),
        "context":"continuous-integration/sympy-pr"
    }
    return requests.post(url, json=payload, headers=get_header())

def add_success_status(sha, commenter):
    url = 'https://api.github.com/repos/isuruf/symengine/statuses/{}'.format(sha)
    payload = {
        "state":"success",
        "target_url":"",
        "description":"{} signed off".format(commenter),
        "context":"continuous-integration/sympy-pr"
    }
    return requests.post(url, json=payload, headers=get_header())


class MainHandler(tornado.web.RequestHandler):
    def post(self):
        headers = self.request.headers
        event = headers.get('X-GitHub-Event', None)

        if event == 'ping':
            self.write('pong')
        elif event == 'issue_comment':
            body = tornado.escape.json_decode(self.request.body)
            pr = body['issue']['number']
            comment = body['comment']['body']
            commenter = body['comment']['user']['login']

            if (comment.lower().find("needs more work") != -1):
                commit_id = get_pr_last_commit(int(pr))
                add_failure_status(commit_id, commenter)
            elif (comment.lower().find("sign off") != -1):
                commit_id = get_pr_last_commit(int(pr))
                add_success_status(commit_id, commenter)
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
