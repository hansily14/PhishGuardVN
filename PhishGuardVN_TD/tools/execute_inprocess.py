"""Execute notebook cells with IPython when this host cannot start ZMQ kernels.
Outputs are actual Python executions, not manufactured notebook results.
"""
import os
from pathlib import Path
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
import matplotlib
matplotlib.use('module://matplotlib_inline.backend_inline')
root=Path(__file__).resolve().parents[1]
os.chdir(root)
shell=InteractiveShell.instance()
for path in sorted((root/'notebooks').glob('*.ipynb')):
    shell.reset(new_session=True)
    book=nbformat.read(path,as_version=4);counter=0
    for cell in book.cells:
        if cell.cell_type!='code':continue
        counter+=1
        with capture_output(display=True) as captured:
            result=shell.run_cell(cell.source,store_history=True)
        if not result.success:
            print(captured.stdout,captured.stderr);raise RuntimeError(f'Notebook failed: {path.name} cell {counter}')
        cell.execution_count=counter;cell.outputs=[]
        if captured.stdout:cell.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
        if captured.stderr:cell.outputs.append(nbformat.v4.new_output('stream',name='stderr',text=captured.stderr))
        for output in captured.outputs:
            cell.outputs.append(nbformat.v4.new_output('display_data',data=output.data,metadata=output.metadata))
    book.metadata['execution_environment']='Executed sequentially using in-process IPython; ZMQ kernel launch blocked on build host.'
    nbformat.validate(book);nbformat.write(book,path)
    print('Executed:',path.name,flush=True)
