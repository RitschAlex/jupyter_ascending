import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { INotebookTracker, NotebookPanel } from '@jupyterlab/notebook';
import { Kernel } from '@jupyterlab/services';

const IS_DEBUG = true;
const TARGET_NAME = 'AUTO_SYNC::notebook';

const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyter_ascending:plugin',
  description: 'A JupyterLab extension to automatically sync notebook changes.',
  autoStart: true,
  requires: [INotebookTracker],
  activate: (app: JupyterFrontEnd, tracker: INotebookTracker) => {
    console.log('Jupyter Ascending extension is activated!');
    tracker.widgetAdded.connect((sender, panel: NotebookPanel) => {
      panel.sessionContext.ready.then(() => {
        const kernel = panel.sessionContext.session?.kernel;
        if (kernel) {
          console.log(`Kernel ready for notebook: ${panel.context.path}`);
          setupComm(panel, kernel);
        }
      });

      panel.sessionContext.kernelChanged.connect((sender, args) => {
        if (args.newValue) {
          console.log(
            `Kernel restarted/changed. Re-registering notebook: ${panel.context.path}`
          );
          args.newValue.requestExecute({
            code: 'import jupyter_ascending.extension; jupyter_ascending.extension.set_everything_up()'
          });

          setupComm(panel, args.newValue);
        }
      });
    });
  }
};

function setupComm(panel: NotebookPanel, kernel: Kernel.IKernelConnection) {
  console.log(
    'Attempting to setup comm for notebook and load python extension:',
    panel.context.path
  );
  kernel.requestExecute({ code: '%load_ext jupyter_ascending' });
  kernel.registerCommTarget(TARGET_NAME, (comm, msg) => {
    comm.onMsg = msg => {
      if (IS_DEBUG) {
        console.log('Precessing a message', msg);
      }
      const data = msg.content.data as any;
      const command = data.command;

      switch (command) {
        case 'start_sync_notebook':
          console.log('Starting to sync notebook:', panel.context.path);
          start_sync_notebook(comm, data, panel);
          break;

        default:
          console.log(`Got an unhandled message (command: ${command}): `, msg);
      }
    };
    comm.onClose = msg => {
      console.log('Comm closed', msg);
    };
  });
}

function get_cells_without_outputs(panel: NotebookPanel) {
  const cells = panel.context.model.cells;
  const cells_cloned = [];

  for (let i = 0; i < cells.length; i++) {
    const cellJSON = cells.get(i).toJSON();
    if (cellJSON.cell_type === 'code') {
      cellJSON.outputs = [];
      cellJSON.execution_count = null;
    }
    cells_cloned.push(cellJSON);
  }
  return cells_cloned;
}

function start_sync_notebook(
  comm: Kernel.IComm,
  data: any,
  panel: NotebookPanel
) {
  comm.send({
    command: 'merge_notebooks',
    javascript_cells: get_cells_without_outputs(panel),
    new_notebook: data.cells
  } as any);
}

export default plugin;
