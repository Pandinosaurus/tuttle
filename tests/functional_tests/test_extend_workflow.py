# -*- coding: utf-8 -*-
from subprocess import check_output, CalledProcessError
from os.path import isfile, join

from os import mkdir
from tests.functional_tests import isolate, run_tuttle_file
from shlex import split
from tuttle.extend_workflow import extract_variables, load_template
from tuttle.utils import CurrentDir
from tuttle.workflow_runner import TuttleEnv


class TestExtendWorkflow:

    def init_tuttle_project(self):
        # Creates .tuttle directory and subdirs for a tuttle project
        project = """file://B <- file://A
    echo A produces B > B"""
        rcode, output = run_tuttle_file(project)
        assert rcode == 0, output

    def get_cmd_extend(self, args_st):
        """
        :return: A command line to call tuttle-extend-workflow even if tuttle has not been installed with pip
        """
        cmd_extend = "{} {}".format('tuttle-extend-workflow', args_st)
        return cmd_extend

    def run_extend_workflow(self, params_st):
        self.init_tuttle_project()  # ensures there is a .tuttle directory
        cmd = self.get_cmd_extend(params_st)
        with TuttleEnv():
            output = check_output(split(cmd))
        return output

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_create_extension_file(self):
        """ Calling tuttle-extend-workflow command creates an extension file in the right directory"""
        output = self.run_extend_workflow('b-produces-x.tuttle x="C"')
        expected_file = join('.tuttle', 'extensions', 'extension')
        assert isfile(expected_file), output

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_create_extension_from_template(self):
        """ A call the tuttle-extend-workflow command creates an extension file and injects variables """
        output = self.run_extend_workflow('b-produces-x.tuttle x="C"')
        expected_file = join('.tuttle', 'extensions', 'extension')
        assert isfile(expected_file), output
        extension = open(expected_file).read()
        rule_pos = extension.find("file://C <- file://B")
        assert rule_pos > -1, extension

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_bad_extension_parameter(self):
        """ When the syntax of parameters for tuttle-extend-workflow is wrong it should fail"""
        try:
            output = self.run_extend_workflow('b-produces-x.tuttle x"C"')
            assert False, "tuttle-extend-workflow should have exited in error"
        except CalledProcessError as e:
            assert e.returncode == 1
            pos_err = e.output.find('Can\'t extract variable from parameter')
            assert pos_err > -1, e.output

    @isolate(['A'])
    def test_bad_template_file(self):
        """ If the template file does not exist, tuttle-extend-workflow is wrong it should fail"""
        try:
            output = self.run_extend_workflow('unknown_template x="C"')
            assert False, "tuttle-extend-workflow should have exited in error"
        except CalledProcessError as e:
            assert e.returncode == 1
            pos_err = e.output.find('Can\'t find template file')
            assert pos_err > -1, e.output

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_create_two_extensions(self):
        """ If tuttle-extend-workflow is called twice, it should create two extension files (with distinct names) """
        self.init_tuttle_project()  # ensures there is a .tuttle directory
        with TuttleEnv():
            cmd = self.get_cmd_extend('b-produces-x.tuttle x="C"')
            output = check_output(split(cmd))
            cmd = self.get_cmd_extend('b-produces-x.tuttle x="D"')
            output = check_output(split(cmd))
        expected_file = join('.tuttle', 'extensions', 'extension')
        assert isfile(expected_file), output
        expected_file = join('.tuttle', 'extensions', 'extension2')
        assert isfile(expected_file), output

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_extend_not_called_from_a_preprocess(self):
        """ tuttle-extend-workflow should fail if not called from a preprocess in tuttle """
        self.init_tuttle_project()  # ensures there is a .tuttle directory
        cmd = self.get_cmd_extend('b-produces-x.tuttle x="C"')
        try:
            output = check_output(split(cmd))
            assert False, output
        except CalledProcessError as e:
            pos_err = e.output.find('Can\'t find workspace')
            assert pos_err > -1, e.output
            assert e.returncode == 1, e.returncode

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_missing_variable(self):
        """ If a variable in the template has no value, tuttle-extend-workflow should fail"""
        try:
            output = self.run_extend_workflow('b-produces-x.tuttle')
            assert False, "tuttle-extend-workflow should have exited in error"
        except CalledProcessError as e:
            pos_err = e.output.find('Missing value for a template variable')
            assert pos_err > -1, e.output
            assert e.returncode == 1, e.returncode

    def test_extract_variable_an_array(self):
        """  simple array should be constructed from the args"""
        args = ['inputs[]=A', 'B']
        variables = extract_variables(args)
        assert isinstance(variables, dict), type(variables)
        assert len(variables) == 1, variables
        assert isinstance(variables['inputs'], list), type(variables['inputs'])
        assert variables['inputs'] == ['A', 'B'], variables['inputs']

    def test_extract_variable_multiple(self):
        """  a complex extract variable case should work """
        args = ['inputs[]=A', 'B', 'C', 'foo=bar']
        variables = extract_variables(args)
        expected = {'inputs': ['A', 'B', 'C'], 'foo' : 'bar'}
        assert variables == expected, variables

    @isolate(['A', 'everything-produces-result.tuttle'])
    def test_variable_array(self):
        """tuttle-extend-workflow can have parameters setting and array for a variable"""
        try:
            output = self.run_extend_workflow('everything-produces-result.tuttle inputs[]=A B C foo=bar')
        except CalledProcessError as e:
            print(e.output)
        expected_file = join('.tuttle', 'extensions', 'extension')
        assert isfile(expected_file), output
        extension = open(expected_file).read()
        rule_pos = extension.find("file://RESULT <- file://A file://B")
        assert rule_pos > -1, extension
        bar_pos = extension.find("**bar**")
        assert bar_pos > -1, extension

    @isolate(['b-produces-x.tuttle'])
    def test_template_can_be_anywhere(self):
        """  the template file could be located anywhere including in .. and path should be with local separator """
        mkdir('test')
        with CurrentDir('test'):
            tpl_path = join('..', 'b-produces-x.tuttle')
            load_template(tpl_path)

    @isolate(['A', 'b-produces-x.tuttle'])
    def test_extension_name(self):
        """ The name of the extension can be chosen by the user"""
        output = self.run_extend_workflow('-n my_extension b-produces-x.tuttle x="C"')
        expected_file = join('.tuttle', 'extensions', 'my_extension')
        assert isfile(expected_file), output

    @isolate(['A', 'everything-produces-result.tuttle'])
    def test_verbosity(self):
        """tuttle-extend-workflow should display what it does when called verbosely"""
        output = self.run_extend_workflow('-v everything-produces-result.tuttle inputs[]=A B C foo=bar')
        pos_template = output.find("everything-produces-result.tuttle")
        assert pos_template >= 0, output
        pos_simple_var = output.find("foo=bar")
        assert pos_simple_var >= 0, output
        pos_complex_var = output.find("inputs[]=A B C")
        assert pos_complex_var >= 0, output
