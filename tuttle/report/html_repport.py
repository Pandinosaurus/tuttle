# -*- coding: utf8 -*-

from jinja2 import Template
from os import path, mkdir, error
from shutil import copytree
from time import strftime, localtime
from dot_repport import dot
from os.path import dirname, join, isdir
import sys


def data_path(*path_parts):
    if getattr(sys, 'frozen', False):
        # The application is frozen
        datadir = join(dirname(sys.executable), "report")
    else:
        # The application is not frozen
        # Change this bit to match where you store your data files:
        datadir = dirname(__file__)
    return join(datadir, *path_parts)



def nice_size(size):
    if size < 1000:
        return "{} B".format(size)
    elif size < 1000 * 1000:
        return "{} KB".format(size / 1024)
    elif size < 1000 * 1000 * 1000:
        return "{} MB".format(size / (1024 * 1024))
    elif size < 1000 * 1000 * 1000 * 1000:
        return "{} GB".format(size / (1024 * 1024 * 1024))


def nice_file_size(filename):
    if not filename:
        return ""
    try:
        file_size = path.getsize(filename)
        if file_size == 0:
            return "empty"
        else:
            return nice_size(file_size)
    except error:
        return "empty"


def format_resource(resource, workflow):
    sig = None
    if resource.url in workflow._resources_signatures:
        sig = workflow._resources_signatures[resource.url]
    return {
        'url': resource.url,
        'signature' : sig,
    }


def format_process(process, workflow):
    duration = ""
    start = ""
    end = ""
    if process.start:
        start = strftime("%a, %d %b %Y %H:%M:%S", localtime(process.start))
        if process.end:
            end = strftime("%a, %d %b %Y %H:%M:%S", localtime(process.end))
            duration = process.end - process.start

    return {
        'id': process.id,
        'processor': process._processor.name,
        'start': start,
        'end': end,
        'duration': duration,
        'log_stdout': process.log_stdout,
        'log_stdout_size': nice_file_size(process.log_stdout),
        'log_stderr': process.log_stderr,
        'log_stderr_size': nice_file_size(process.log_stderr),
        'outputs': (format_resource(resource, workflow) for resource in process.iter_outputs()),
        'inputs': (format_resource(resource, workflow) for resource in process.iter_inputs()),
        'code' : process._code,
        'success': process.success,
    }


def ensure_assets(dest_dir):
    assets_dir = path.join(dest_dir, 'html_report_assets')
    if not path.isdir(assets_dir):
        copytree(data_path('html_report_assets', ''), assets_dir)


def create_html_report(workflow, filename):
    """ Write an html file describing the workflow
    :param workflow:
    :param filename: path to the html fil to be generated
    :return: None
    """
    file_dir = path.dirname(filename)
    ensure_assets(file_dir)
    tpl_filename = data_path("report_template.html")
    with open(tpl_filename, "r") as ftpl:
        t = Template(ftpl.read())
    processes = [format_process(p, workflow) for p in workflow.iter_processes()]
    with open(filename, "w") as fout:
        fout.write(t.render(processes=processes, dot_src=dot(workflow)))
