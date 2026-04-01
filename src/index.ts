import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import {
  INotebookTracker,
  NotebookActions,
  NotebookPanel
} from '@jupyterlab/notebook';
import { Cell } from '@jupyterlab/cells';
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

      // Handle kernel restarts or changes
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
        case 'op_code__delete_cell':
          op_code__delete_cell(panel, data);
          break;
        case 'op_code__insert_cell':
          op_code__insert_cell(panel, data);
          break;
        case 'op_code__replace_cell':
          op_code__replace_cell(panel, data);
          break;
        case 'update_cell_contents':
          update_cell_contents(panel, data);
          break;
        case 'finish_merge':
          comm.send({ command: 'merge_complete' });
          break;
        case 'restart_kernel':
          kernel.restart();
          break;
        default:
          console.log(`Got an unexpected message (command: ${command}): `, msg);
      }
    };
    comm.onClose = msg => {
      console.log('Comm closed', msg);
    };
  });
}

function get_cell_from_notebook(
  panel: NotebookPanel,
  cell_number: number
): Cell {
  const notebook = panel.content;
  while (cell_number >= notebook.widgets.length) {
    notebook.model?.sharedModel?.insertCell(notebook.widgets.length, {
      cell_type: notebook.notebookConfig.defaultCell
    });
  }
  return notebook.widgets[cell_number];
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

function update_cell_contents(panel: NotebookPanel, data: any) {
  const notebook = panel.content;
  const cell = get_cell_from_notebook(panel, data.cell_number);
  // const sharedModel = panel.context.model.sharedModel;

  cell.model.sharedModel.setSource(data.cell_contents);

  if (cell.model.type !== data.cell_type) {
    notebook.activeCellIndex = data.cell_number;
    NotebookActions.changeCellType(notebook, data.cell_type);
  }
}

function op_code__replace_cell(panel: NotebookPanel, data: any) {
  console.log('Replacing cell...', data);
  update_cell_contents(panel, data);
}

function op_code__insert_cell(panel: NotebookPanel, data: any) {
  console.log('Inserting cell...', data);
  const sharedModel = panel.context.model.sharedModel;

  sharedModel.insertCell(data.cell_number, {
    cell_type: data.cell_type,
    source: data.cell_contents
  });
}

function op_code__delete_cell(panel: NotebookPanel, data: any) {
  console.log('Deleting cell...', data);
  const sharedModel = panel.context.model.sharedModel;

  // Sort descending to avoid messing up indices when deleting multiple cells
  const indices_to_delete = (data.cell_indices as number[]).sort(
    (a, b) => b - a
  );

  sharedModel.transact(() => {
    for (const index of indices_to_delete) {
      if (index < sharedModel.cells.length) {
        sharedModel.deleteCell(index);
      }
    }
  });
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
