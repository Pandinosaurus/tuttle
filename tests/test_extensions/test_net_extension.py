# -*- coding: utf8 -*-
from os.path import isfile, join

from tests.functional_tests import isolate, run_tuttle_file
from tuttle.project_parser import ProjectParser
from tuttle.extensions.net import HTTPResource


class TestHttpResource():

    def test_real_resource_exists(self):
        """A real resource should exist"""
        # TODO : change this when tuttle has its site... If it can handle the load...
        # Or by a local http server
        res = HTTPResource("http://www.google.com/")
        assert res.exists()

    def test_fictive_resource_exists(self):
        """A real resource should exist"""
        res = HTTPResource("http://www.example.com/tuttle")
        assert not res.exists()

    def test_http_resource_in_workflow(self):
        """An HTTP resource should be allowed in a workflow"""
        pp = ProjectParser()
        project = "file://result <- http://www.google.com/"
        pp.set_project(project)
        workflow = pp.parse_project()
        assert len(workflow._processes) == 1
        inputs = [res for res in workflow._processes[0].iter_inputs()]
        assert len(inputs) == 1

    # TODO : should we follow resources in case of http redirection ?
    def test_resource_etag_signature(self):
        """ An HTTPResource with an Etag should use it as signature """
        res = HTTPResource("http://www.example.com/")
        sig = res.signature()
        assert sig == 'Etag: "359670651"', sig

    def test_resource_last_modified_signature(self):
        """ An HTTPResource with an Last-Modified should use it as signature in case it doesn't have Etag"""
        res = HTTPResource("http://www.wikipedia.org/")
        sig = res.signature()
        assert sig == 'Last-Modified: Sun, 19 Apr 2015 19:01:00 GMT', sig

    def test_ressource_signature_without_etag_nor_last_modified(self):
        """ An HTTPResource signature should be a hash of the beginning of the file if we can't rely on headers """
        res = HTTPResource("http://www.4chan.org/legal")
        sig = res.signature()
        assert sig == 'sha1-32K: fc0e8360cb576610d54df896a08f1b799b796a3b', sig


class TestDownloadProcessor():

    @isolate
    def test_standard_download(self):
        """Should download a simple url"""
        project = " file://google.html <- http://www.google.com/ #! download"
        pp = ProjectParser()
        pp.set_project(project)
        workflow = pp.parse_and_check_project()
        workflow.static_check_processes()
        workflow.run()
        assert isfile("google.html")
        content = open("google.html").read()
        assert content.find("<title>Google</title>") >= 0
        logs = open(join(".tuttle", "processes", "logs", "__1_stdout"), "r").read()
        assert logs.find("\n.\n") >= 0
        assert isfile(join(".tuttle", "processes", "logs", "__1_err"))

    @isolate
    def test_long_download(self):
        """ Progress dots should appear in the logs in a long download"""
        project = " file://jquery.js <- http://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js #! download"
        pp = ProjectParser()
        pp.set_project(project)
        workflow = pp.parse_and_check_project()
        workflow.static_check_processes()
        workflow.run()
        assert isfile("jquery.js")
        logs = open(join(".tuttle", "processes", "logs", "__1_stdout"), "r").read()
        assert logs.find("...") >= 0

    @isolate
    def test_pre_check(self):
        """Should fail if not http:// <- file:// """
        project = " http://www.google.com/ <-  #! download"
        pp = ProjectParser()
        pp.set_project(project)
        workflow = pp.parse_and_check_project()
        try:
            workflow.pre_check_processes()
            assert False, "An exception should be raised"
        except:
            assert True


    # @isolate
    # def test_download_fails(self):
    #     """Should raise an exception if download fails"""
    #     project = " file://tuttle.html <- http://www.example.com/tuttle #! download"
    #     pp = ProjectParser()
    #     pp.set_project(project)
    #     # Don't check project or execution of the workflow will not be allowed because input resource is missing
    #     workflow = pp.parse_project()
    #     print workflow._processes
    #     print [res.url for res in workflow._processes[0].inputs]
    #     workflow.prepare_execution()
    #     workflow.run()
    #     assert isfile("tuttle.html")

    @isolate
    def test_pre_check_before_running(self):
        """ Pre check should happen for each process before run the whole workflow """
        project = """file://A <-
        obvious failure
file://google.html <- file://A #! download
        """
        rcode, output = run_tuttle_file(project)
        assert rcode == 2
        assert output.find("Download processor") >= 0, output

    @isolate
    def test_pre_check_before_invalidation(self):
        """Pre check should happen before invalidation"""
        project1 = """file://A <-
        echo A > A
        """
        rcode, output = run_tuttle_file(project1)
        assert isfile('A')
        project2 = """file://A <-
        echo different > A
file://google.html <- file://A #! download
        """
        rcode, output = run_tuttle_file(project2)
        assert rcode == 2
        assert output.find("* file://B") == -1
        assert output.find("Download processor") >= 0, output
