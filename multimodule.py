"""Possible windows only tool to convert packages of .pyx and .py files into single Cython extensions.
Arguments:
method: (1,2)
Select which method is used to build the Cython extension.
If you don't set a value or set it to 1, generate a DLL with one PyInit export symbol for each module, and an importer that activates when you import the main module and allows you to easily import other modules.
This method supports .py and .pyx files, and it can handle just about anything that Cython can Cythonize.
Note that the import symbols are filled in with random letters, to allow multiple modules with similar names.


If you set method to 2, creates a single .pyx file by creating a function for each module. When that module is imported, that function returns locals(), which is dumped into a modules namespace.
The functions are declared using cdef, so they don't clutter up the namespace and a dictionary is stored mapping module names to there functions.
This method creates slightly smaller binaries and only exports one function.
However, it's not as compatable as method 1.
Most code you can write in pure Python works as far as I know, but Cython, for example, won't let you use cdef to declare functions with method 2, since that would create functions inside functions.
Note: Since this method might be able to turn packages into single.pyx files, you might want to distribute those files if you release code. Only Cython is required to compile those files.
To do this, compile a package with this tool, then open up the build_temp directory and look for a .pyx file matching the main module. This should be the same name as your package. Copy this file to your package and store it.

package:
Bool specifying weather or not to set the modules to import from the main module or to import globally.
Example, if you have a package named somecode and a module somecode.constants, with package off you'll import constants, with package on you type import somecode.constants, assuming you set somecode as the main module.
It sets all the stored modules to live under the main module.

encoding:
The encoding to use for loading input files.
Default UTF-8
If you have chardet installed, that can be used if you don't specify an encoding.

main_module:
Set which .py or .pyx file should be used as the starting module. It will be guessed if you don't set it.

files (required):
A list of comma seperated names, either of files or directories, to include.
If it's a file, the script will look for a file that has a .py or .pyx extension.
If it's a directory, the script will treat that directory as a package and try to include anything in it.

Note: The script stores all the left over junk in the build_temp directory. It's safe to delete.

"""
__version__='0.6'
__author__="Keith"



_cached_names={}
def get_name(loc, name=None):
	loc=path.abspath(loc)
	if loc in _cached_names: return _cached_names[loc]
	if not name:
		name=path.split(loc)[1]
		name=path.splitext(name)[0]
	d=path.dirname(loc)
	packages=[]
	v=d.split(path.sep)
	for i in range(len(v), -1, -1):
		part=v[:i]
		part=path.sep.join(part)
		n=part.split(path.sep)[-1]
		for j in ext:
			loc=path.join(part, "__init__"+j)
			if path.exists(loc) and path.isfile(loc):
				packages.insert(0, n)
				break
		else: break

	packages.append(name)
	if len(packages)<2: return name
	else:
		name='.'.join(packages)
		_cached_names[loc]=name
		return name

def eprint(*args, **kwargs): return print(*args, file=sys.stderr, **kwargs)


class mod:
	"""A class to hold data about modules"""
	__slots__=("file", "name", "shortname", "cfile", "pyfile") # The list of attributes that'll be set.

	def __init__(self, **kwargs):
		for i in kwargs.keys(): setattr(self, i, kwargs[i])

	def __repr__(self): return f"<Module {self.name}, {self.file}>"

	def __eq__(self, other):
		if isinstance(other, str): return self.name==other
		else: return object.__eq__(self, other)

def get_random_letters(length=30):
	letters="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
	res=""
	for i in range(length): res+=random.choice(letters)
	return res


embedded_code="""
__path__=(__file__,)
__package__=__name__
if '__spec__' in globals(): __spec__.submodule_search_locations=__path__ # This should hopefully allow relative imports.
cimport cython
@cython.auto_pickle(False)
cdef class multimodule_importer:
	cdef str name, file, package

	def __init__(self):
		try:
			import os.path as path
			self.file=path.abspath(__file__)
		except:
			self.__file__=__file__

		self.name=__name__
		self.package=__package__
		import importlib, importlib.machinery


	cdef _find_spec(self, str name):
		import importlib.machinery, importlib
		has_submodules=False
		sp=None
		for i in __module_dict__:
			if i.startswith(name+"."):
				has_submodules=True
				break
		if name in __module_dict__:
			sp=importlib.machinery.ModuleSpec(name=name, loader=self, origin=self.file, is_package=has_submodules)
		if sp is None and has_submodules==True:
			sp=importlib.machinery.ModuleSpec(name=name, loader=None, origin=None, is_package=True)
		if sp is not None and has_submodules==True:
			sp.submodule_search_locations=(self.file,)
		if sp is not None: sp.has_location=True
		return sp

	def find_spec(self, str name, *args, **kwargs):
		#{protect_find_spec}
		return self._find_spec(name)

	def create_module(self, *args, **kwargs): return None

	def exec_module(self, module):
		import _imp, importlib, importlib.machinery
		spec=module.__spec__
		fakespec=importlib.machinery.ModuleSpec(name=__module_dict__[spec.name], origin=spec.origin, loader=None)
		temp=_imp.create_dynamic(fakespec, fakespec.origin)
		temp.__spec__=spec
		temp.__name__=spec.name
		temp.__package__=temp.__spec__.parent
		_imp.exec_dynamic(temp)
		data=temp.__dict__
		module.__dict__.update(data, **module.__dict__)
		setattr(module, "__doc__", data.get("__doc__", None))
		return

import sys
sys.meta_path.insert(0, multimodule_importer())
del sys
"""
def global_import(*modules):
	# This just imports modules and makes them globally available.
	import importlib
	for i in modules:
		globals()[i]=importlib.import_module(i)





def clean_temp(location):
	while location in os.getcwd(): os.chdir("..")
	files, dirs=find_files(location, add_folders=True, multiple_lists=True)
	import shutil
	shutil.rmtree(location)
	print("Cleaned the temp directory, removing ", len(files), "files and", len(dirs), "folders")
	return

def die(*args, **kwargs):
	eprint(*args, **kwargs)
	sys.exit(10)

def make_directory_tree(location):
	location=path.dirname(location)
	location=location.split(path.sep)
	curpath=path.abspath(".")
	for i in location:
		curpath=path.join(curpath, i)
		if not path.exists(curpath): os.mkdir(curpath)






def files_to_module(f, package, main_module_name):
	mods=[]
	for i in f:
		name=get_name(i)
		if package==True and not name.startswith(main_module_name+"."): name=main_module_name+"."+name
		if package==False and name.startswith(main_module_name+".", 1): name=name.replace(main_module_name+".", "")
		if name.endswith(".__init__"):
			name=name.rsplit(".__init", 1)[0]
		shortname=name.split(".")[-1]
		file=path.abspath(i)
		mods.append(mod(name=name, shortname=shortname, file=file))
	return mods

def index_range(iterator):
	iterator=iter(iterator)
	i=0
	while True:
		try: yield (i, next(iterator))
		except StopIteration: return
		i+=1









def find_file_in_directories(dirs, filename, exts):
	for i in dirs:
		for j in exts:
			file=path.join(i, filename)+j
			if path.exists(file): return path.abspath(file)
			else: file=path.join(i, filename.replace(".", path.sep)+j)

			if path.exists(file): return path.abspath(file)

	return None






def open_file(filename, encoding="*", skip_unreadable=False, split=True):
	if not 'chardet' in globals(): import chardet
	p=None
	if not path.exists(filename):
		die("Can't find file "+filename)

	if encoding=="*":
		p=open(filename, "rb")
		import chardet
		d=chardet.UniversalDetector()
		length=p.seek(0, 2)
		p.seek(0, 0)
		while d.done==False and p.tell()<length: d.feed(p.read(50))
		charencoding=d.close()["encoding"]
		p=open(filename, mode="r", encoding=charencoding)
	else: p=open(filename, mode="r", encoding=encoding)
	try:
		lines=p.readlines(2)
		for i in lines:
			if i.startswith("#") and 'coding' in i:
				i=i.strip()
				if i.startswith("-*-") and i.endswith("-*-"):
					i=i.split("-*- coding: ", 1)[0].strip(" -*-")
					print("Found encoding "+i, filename)
					p=open(filename, encoding=i, mode="r")
					break
			if i.startswith("#coding="):
				i=i.split("#coding=", 1)[1].strip()
				p=open(filename, mode="r", encoding=i)
				break
		p.seek(0)
		data=p.read()
		p.close()
	except UnicodeDecodeError:
		if p: p.close()
		if skip_unreadable==False: die("Can't decode "+filename+" with encoding "+p.encoding)
		else: raise
	if split==True: data=data.splitlines(True)
	return data


def add_files(modules, build_temp):
	search_for=[".pxd", ".pxi"]
	for i in modules:
		file, ext=path.splitext(i.file)
		for j in search_for:
			filename=path.join(file, j)
			if not path.exists(filename):
				filename=path.join(path.dirname(i.file), i.shortname)+j
			if path.exists(filename):
				dest=path.join(build_temp, i.name)+j
				with open(filename, "rb") as f: data=f.read()
				with open(dest, "wb") as f: f.write(data)


def add_include_locations(val, func, splitstr=","):
	if len(val)==0: return
	for i in val.split(splitstr):
		if not path.exists(i): eprint(i, "does not exist. This error happened when checking C files")
		func(path.abspath(i))




def protect_importer(data, funcname):
	find_spec="""
		if not name in __module_dict__: return None
		try: val="""+funcname+"""(name)
		except: val=False
		if val==False: return None
"""
	data=data.format(protect_find_spec=find_spec)
	return data


startswith_hints=("from ", "import ", "cimport ")
def find_imports(file, name, resolve_relative=True):
	from importlib.util import resolve_name
	results=set()
	with open(file, mode="r", encoding="UTF-8") as f: data=f.read()
	data=data.splitlines(False)
	possible_imports=tuple(i.lstrip(" 	") for i in data if i.lstrip(" 	").startswith(startswith_hints))
	for i in possible_imports:
		i=i.replace("cimport", "import")
		if i.startswith("import"):
			val=i.split(" ", 1)[1]
			val=tuple(j.strip() for j in val.split(","))
			val=tuple(j.split(" ")[0].strip() for j in val)
			results.update(val)
			continue
		elif i.startswith("from"):
			val=i.split(" ", 3)
			source=val[1]
			val=tuple(source+"."+j.strip().split(" ", 2)[0] for j in val[3].split(", "))
			results.update(val)
	for i in tuple(results):
		if i.count(".")==1: continue
		lst=i.split(".")
		while True:
			del lst[-1]
			if len(lst)==0: break
			text='.'.join(lst)
			if len(text)==0: break
			results.add(text)
	if resolve_relative==True:
		package_name=name.split(".")[:-1]
		package_name='.'.join(package_name)
#  print(package_name, results)
		results={resolve_name(i, package_name) for i in results}
	return results



def locate_modules(files, ext=(".pyx", ".py", ".pyw")):
	if isinstance(files, str): files=(files,)
	f=[]
	dirs=[]
	dir_locations=["."]
	dir_locations.extend(sys.path)
	current_files=glob("*.*")
	for i in tuple(files):
		result=find_file_in_directories(dir_locations, i, ext)
		if result is not None:
			f.append(result)
			continue
		if path.exists(i) and path.isfile(i):
			f.append(i)
			continue
		possible_dirs=tuple(path.join(j, i) for j in dir_locations if path.exists(path.join(j, i)) and path.isdir(path.join(j, i)))
		if len(possible_dirs)>0:
			loc=possible_dirs[0]
			if path.exists(loc) and path.isdir(loc):
				results=find_files(loc, extensions=ext)
				if len(files)>0:
					f.extend(results)
				continue
		die("Failed to find "+i)
	return f


def fix_future(data, output=None):
	if output==None: output=data
	for i in range(len(data)):
		line=data[i]
		if line.lstrip().startswith("from __future__ import"):
			data[i]="\n"
			if not line in data and not line.lstrip() in data: output.insert(0, line.lstrip())
	return output

def fix_docstring(data):
	doc_markers=('"""', "'''", "'", '"')
	for i in range(len(data)):
		line=data[i]
		if line.startswith(doc_markers):
			print("Found docstring at line "+str(i)+", "+line)
			data[i]="__doc__="+data[i]+"\n"
			break
	return data


def fix_exceptions(data):
	for i in data:
		line=i.strip()
		if line.startswith("except "):
			part=line.replace("except ", "").split(":")[0]
			part=part.split(",")
			for j in part:
				j=j.split(".")
				if len(j)==1: continue
				required_module='.'.join(j[:-1])
				print(required_module, "required")
				required_module="import "+required_module+"\n"
				for k in data:
					k=k.strip()
					if k.startswith((required_module, "from "+'.'.join(j[1:-1])+" import "+j[-1])): break
				else: data.insert(0, required_module)
				print("Added "+k)
	return data
def get_docstring(data):
	import re
	r=re.compile(r'''(['"'"'"]{1,3})(\.)\1''')
	return r.match(data)

class clang_compiler:
	# My attempt to make some basic ability to compile with the windows port of clang, mostly.
	__slots__=("exe", "exe_ext", "lib_dirs", "include_dirs")
	def __init__(self):
		import shutil, sysconfig
		exe=shutil.which("clang")
		if exe==None: die("Couldn't find clang, try putting it on the path environment variable.")
		self.exe=exe
		self.exe_ext=sysconfig.get_config_var("EXE")
		self.include_dirs=[]
		self.lib_dirs=[]

	add_include_dir=lambda self, dir: self.include_dirs.append(dir)
	add_library_dir=lambda self, dir: self.lib_dirs.append(dir)

	def compile(self, cfiles, extra_postargs=''):
		results=[]
		import subprocess, os.path as path
		cincludes=''
		for i in self.include_dirs:
			cincludes+=f"-I{i} "
		for i in cfiles:
			output_name=path.splitext(i)[0]+".o"
			result=subprocess.run(f"{self.exe} -o{output_name} -O3 -w {cincludes} {i} -c {extra_postargs}", shell=True)
			if result.returncode!=0: raise Exception("Couldn't compile "+i)
			results.append(output_name)
		return results

	def link_shared_object(self, objects, output_name, export_symbols=(), extra_postargs=''):
		import subprocess
		objs=' '.join(objects)
		libs=''
		for i in self.lib_dirs: libs+="-L"+i+" "
		res=subprocess.run(f"{self.exe} {libs} -o{output_name} -shared {objs} {extra_postargs}", shell=True)
		if res.returncode!=0: raise Exception("Failed to compile object files"+objs)

def fix_module(data, name):
	#data=fix_docstring(data)
	data=list(i.expandtabs(1) for i in data)
	#data=fix_exceptions(data)
	data=fix_future(data)
# data=fix_relative(data)
	return data


def find_files(location, add_folders=False, add_files=True, extensions=("*",), multiple_lists=False):
	if multiple_lists==False: results=[]
	else: files, folders=[], []
	scan=[]
	scan.append(os.scandir(location))
	add_any_files="*" in extensions
	while True:
		i=scan[0]
		try: val=next(i)
		except StopIteration:
			del scan[0]
			i.close()
			if len(scan)==0: break
			else: continue
		valpath=path.abspath(val.path)
		if val.is_dir():
			if add_folders==True:
				if multiple_lists==False: results.append(valpath)
				else: folders.append(valpath)
			scan.append(os.scandir(valpath))
		elif val.is_file():
			if add_files==True and add_any_files or path.splitext(valpath)[1] in extensions:
				if multiple_lists==False: results.append(valpath)
				else: files.append(valpath)
	if multiple_lists==False: return results
	else: return files, folders

def main(main_module: "The package or module name of the main module, which is the module which will be imported first by the user", *files: "A space seperated list of module or package names minus the extension that will be searched for in the current directory and on sys.path", package: "Specify weather to import from the main module, or to import modules globally"=False, method: "Select which method to use to build the Cython extension"="1", encoding: "The text encoding to use for the files, default is UTF-8"="UTF-8", import_all: "Cause the extension, when imported, to load all the contained modules"=False, name: "The name of the main module, don't set to use the default"=None, show_modules: "Set weather the extension module will have a list attribute called modules which lists the modules contained in it, default  is False"=False, exe: "Weather to make an exe that starts the main module when launched and can still load other modules. WARNING! Only works for method 2! "=False, protect_function: "The name of a function in the main module that is called whenever a module is about to be imported. If the function returns False, the importing is stopped and if it returns True, it is allowed to continue"=None, compiler_options: "Comma seperated list of compiler options"='', no_cython_processes: "You seem to need to use this option when setting custom compiler directives. This option compiles your Cython code using only the current process. This is slower, but otherwise the compiler directives don't carry across processes."=False, keep_temp: "Set this option to stop the build_temp from being deleted"=False, build_temp: "Set where the build_temp directory should be put"='', output: "Set where the resulting Python extension module is placed, leave empty to use the default settings"='', compiler_directives: "A comma seperated set of compiler directives to pass to Cython"='', cinclude: "A list of comma seperated directory names that will be used to search for extra required C files"='', clib: "A comma seperated list of C libraries to link with"='', prompt: "Weather to prompt for the removal of temporary dirs or files, default is True"=True, init_code: "Allows you to insert extra code by specifying a filename that you need run before the multimodule importer runs. Warning! This code will not have access to the embedded modules, but it will still be embedded. If you want to store a docstring for the main module, you can put it in the embedded code"=None, verbose: "control the verbosity level, the lower the quieter, default is 2."=2, exclude_unused: "Tries to determin all the imported modules and removes any extra modules from the extension that aren't used by the rest. Default is False."=False, exclude_modules: "A comma seperated list of module names to include."="", ccompiler: "The compiler to use to compile the code. Any uses distutils.ccompiler.new_compiler,."="", extra_compile_args: "Extra args to pass on to the c compiler"="", extra_link_args: "Extra args to pass onto the linker"=""):
	__doc__
	global cythonize, glob, path, CythonOptions, ModuleSpec, begin, os, sys, random, traceback, tempfile, importlib, chardet, multiprocessing, ext, tempdir
	from Cython.Build import cythonize
	from Cython.Compiler import Options as CythonOptions
	from distutils.ccompiler import new_compiler
	from distutils.command.build_ext import customize_compiler, build_ext
	from distutils.dist import Distribution
	from importlib.machinery import ModuleSpec
	from glob import glob
	import begin, os, sys, random, traceback, tempfile, importlib, sysconfig
	from os import path
	try: import chardet
	except ImportError: chardet=None
	try: import multiprocessing
	except ImportError: multiprocessing=None
	from Cython.Compiler.Errors import CompileError
	extra_ext=(".pyx",)
	ext=tuple(importlib.machinery.all_suffixes())+extra_ext

	mods=[]
	if prompt==True:
		prompt_func=lambda info: input(info+"Enter anything to exit, or just press enter to continue")
	else:
		prompt_func=lambda info: ''
	say_something=lambda *args, **kwargs: print(*args, **kwargs)
	say_nothing=lambda *args, **kwargs: None
	say_something_important=say_something_interesting=say_anything=print
	try: verbose=int(verbose)
	except ValueError: die("Invalid value for verbose, expected int but got ", verbose)
	if verbose<0 or verbose>3: die("Verbose is not in the expected range (0,2)")
	if verbose<2: say_anything=say_nothing
	if verbose<1: say_something_interesting=say_nothing
	main_module_name=get_name(main_module)
	say_something_interesting("Modules:", ', '.join((main_module,)+files))
	f=[]
	say_anything("Checking files...")
	ext=(".pyx", ".py", ".pyw")
	f=locate_modules(files, ext=ext)
	main_files=locate_modules(main_module, ext=ext)
	if len(main_files)==0: die("Couldn't find main module")
	extra_compile_args=extra_compile_args.split(" ")
	extra_link_args=extra_link_args.split(" ")
	if not build_temp:
		build_temp=path.join(tempfile.gettempdir(), "multimodule_build_temp"+get_random_letters(5))
	tempdir=build_temp # Remember the temp dir so we can clean it up if the app crashes.
	if path.exists(build_temp):
		res=prompt_func("The temporary directory "+build_temp+" already exists")
		if res: die("Exiting")
		else: clean_temp(build_temp)
	os.mkdir(build_temp)
	output_ext=".pyd"
	if not sys.platform=="win32": output_ext=".so"
	if not output:
		output=main_module_name+output_ext
		output=path.abspath(output)
	if path.exists(output):
		for i in sys.modules.values():
			if vars(i).get("__file__", "")==output:
				die("The file "+output+" already exists and is loaded as module "+str(i)+". You'll need to remove it manually before you can successfully compile.")
		res=prompt_func("Warning, output file "+output+" already exists. ")
		if len(res)>0: sys.exit(10)
	bare_output=path.splitext(output)[0]
	say_anything("Main module: ", main_module_name)
	say_something_interesting("Output filename: ", output)
	mods=files_to_module(f, package, main_module_name)
	if len(main_files)>1: # This is hopefully a package
		init_name=main_module_name+".__init__"
		for i in main_files:
			if get_name(i)==init_name:
				main_module=i
				main_files.remove(i)
				mods.extend(files_to_module(main_files, package, main_module_name))
				break
		else: die("The main module "+main_module+" seems to be a package, but the __init__ file can't be found. The program is trying to find ", init_name)
	else:
		main_module=main_files[0]
	main_module_object,=files_to_module((main_module,), package, main_module_name)
	if compiler_options:
		compiler_options=compiler_options.replace(",", "\n")
		compiler_options=compile(compiler_options, "setting up compiler options", "exec", optimize=2)
		opts={}
		exec(compiler_options, opts, opts)
		if '__builtins__' in opts: del opts["__builtins__"]
		if len(opts)>0:
			say_something_interesting("Compiler options set: ", ', '.join(opts.keys()))
		for i in opts.keys():
			setattr(CythonOptions, i, opts[i])
		if len(opts)>0 and no_cython_processes==False:
			eprint("Warning: Cython will compile files with only a single process in order to allow the compiler options you've set to take effect")
			no_cython_processes=True
	directives={}
	if compiler_directives:
		compiler_directives=compiler_directives.replace(",", "\n")
		compiler_directives=compile(compiler_directives, "setting up compiler directives", "exec", optimize=2)
		exec(compiler_directives, directives, directives)
		if '__builtins__' in directives: del directives["__builtins__"]
		say_anything("Compiler directives set: ", ', '.join(directives.keys()))
	say_anything("Building main module...")
	add_files(tuple(mods)+(main_module_object,), build_temp)
	main_location=path.join(build_temp, main_module_name+".pyx")
	main_location=path.abspath(main_location)
	if exclude_unused==True:
		say_anything("Trying to find unused modules...")
		imported_list=find_imports(main_module_object.file, main_module_object.name)
		for i in mods:
			imported_list.update(find_imports(i.file, i.name))
		for i in tuple(mods):
			if not i.name in imported_list:
				say_something_interesting("Module "+i.name+" isn't imported anywhere so it was removed from the compilation.")
				mods.remove(i)
		if len(mods)==0: die("No modules were left after removing unused ones.")
	if exclude_modules:
		for i in exclude_modules.split(","):
			if not i in mods:
				eprint(f"Warning, module {i} was supposed to be excluded, but was never included in the first place!")
				continue
			mods.remove(i)
			say_anything("Directly excluded "+i)
			for j in tuple(mods):
				if j.name.startswith(i+"."): # Remove submodules of a package
					say_anything("Recursively excluded "+j.name)
					mods.remove(j)
	add_importer=len(mods)>0
	p=open(main_location, "w", encoding="UTF-8")
	if not path.exists(main_module) or not path.isfile(main_module):
		die("Main module "+main_module+" could not be found")
	data=open_file(main_module, encoding=encoding)
	names={}
	for i in mods:
		j="PyInit_"+get_random_letters(8)
		while j in names.values(): j+=get_random_letters(1)
		names[i.name]=j
	p.write("#coding: UTF-8\n")
	if init_code:
		init_file=open_file(init_code, encoding=encoding)
		p.writelines(init_file)
		p.write("\n\n") # Make sure there are no bits of code on the same line.
		say_something_interesting("Embedded code from "+init_code+" at the start of "+main_module_name)


	if add_importer:
		p.write("cdef dict __module_dict__={\n")
		for i in names:
			p.write(" '"+i+"':'"+names[i].replace("PyInit_", "")+"',\n")
		p.write("}")
	if show_modules==True:
		f.append("\nmodules=[")
		for i in names: f.append("'"+i+"',")
		f.append("]\n")
	if add_importer:
		importer=embedded_code
		if protect_function!=None: importer=protect_importer(importer, protect_function)
		p.write(importer)
		p.write("\n\n")
	p.writelines(data)
	if import_all==True:
		for i in names: p.write("import "+i+"\n")

	p.close()
	data=open_file(main_location, encoding="UTF-8")
	data=fix_module(data, main_module_name)
	with open(main_location, mode="w", encoding="UTF-8") as p: p.writelines(data)
	say_anything("Compiling...")
	cythonize_files=[]
	mods.append(mod(name=main_module_name, shortname=main_module_name, file=main_location, pyfile=main_location))
	os.chdir(build_temp)
	for i in mods:
		if i.name==main_module_name: continue
		relname=i.name
		relname+=path.splitext(i.file)[1]
		i.pyfile=relname
		contents=open_file(i.file, encoding=encoding)
		s=open(relname, "w", encoding="UTF-8")
		s.write("#coding: UTF-8\n")
		contents=fix_module(contents, i.name)
		s.writelines(contents)
		s.close()
		cythonize_files.append(relname)
	cythonize_files.append(path.relpath(main_location))
	nthreads=0
	if not multiprocessing==None: nthreads=os.cpu_count()
	if no_cython_processes==True: nthreads=0
	try:
		results=cythonize(cythonize_files, language_level="3", compiler_directives=directives, nthreads=nthreads, quiet=verbose<1)
	except CompileError:
		die("Failed to cythonize the code")
	cfiles=[]
	for i in results:
		for j in mods:
			if j.name==i.name: break
		if not j.name==i.name: die("Error when compiling Cython code. Cannot find module in the mods list with name "+str(i.name))
		valid=tuple(k for k in i.sources if path.relpath(k).startswith(j.name))
		if len(valid)!=1: die("Error with sources for "+str(i)+". Can't decide which one to use. ", valid)
		src=path.abspath(valid[0])
		cfiles.append(src)
		j.cfile=src
	for i in mods:
		realname=i.name
		name=i.shortname
		if realname==main_module_name and realname not in names:
			continue
		if not path.exists(i.cfile): die("Unknown error. C code file "+i.cfile+" should exist but doesn't")
		with open(i.cfile, "r", encoding=encoding) as f: data=f.read()
		data=data.replace("PyInit_"+name, names[realname])
		say_anything("Replaced PyInit_"+name+" with "+names[realname])
		with open(i.cfile, "w", encoding=encoding) as f: f.write(data)
	dist=Distribution()
	cmd=build_ext(dist)
	cmd.finalize_options()
	#This modified code snippet was taken from distutils.command.build_ext.run
	if not ccompiler: ccompiler=cmd.compiler
	com=new_compiler(compiler=ccompiler, verbose=verbose>=3)
	customize_compiler(com)
	if cmd.include_dirs is not None:
		com.set_include_dirs(cmd.include_dirs)
	if cmd.define is not None:
		for (name, value) in cmd.define:
			com.define_macro(name, value)
	if cmd.undef is not None:
		for macro in cmd.undef:
			com.undefine_macro(macro)
	if cmd.libraries is not None:
		com.set_libraries(cmd.libraries)
	if cmd.library_dirs is not None:
		com.set_library_dirs(cmd.library_dirs)
	if cmd.rpath is not None:
		com.set_runtime_library_dirs(cmd.rpath)
	if cmd.link_objects is not None:
		com.set_link_objects(cmd.link_objects)




	try: objs=com.compile(cfiles, extra_postargs=extra_compile_args)
	except Exception as e:
		input(e)
		import traceback
		print(traceback.format_exc())
		eprint("Couldn't compile the C files to object code")
		sys.exit()
	say_anything("Linking...")
	symbols=list(names.values())
	symbols.append("PyInit_"+main_module_name)
	try: com.link_shared_object(objs, output, export_symbols=symbols, extra_postargs=extra_link_args)
	except:
		eprint("Oops, something broke")
		sys.exit()
	if keep_temp==False:
		clean_temp(build_temp)
	else:
		say_something_important("The temporary directory is at "+build_temp)
	say_something_important("All done! Created "+output)
	if __name__=="__main__": sys.exit(0)

tempdir=None
if __name__=="__main__":
	import begin.main
	app=begin.main.Program(main)
	try:
		app.start()
	except:
		import os, time, sys, os.path as path, traceback
		if tempdir and path.exists(tempdir):
			import multiprocessing
			while len(multiprocessing.active_children())>0:
				for i in multiprocessing.active_children():
					if not i.is_alive(): i.close()
				if len(multiprocessing.active_children())==0: break
				time.sleep(0.009)
			clean_temp(tempdir)
		type=sys.exc_info()[0]
		if not type==SystemExit:
			print(traceback.format_exc())
			sys.exit(10)


