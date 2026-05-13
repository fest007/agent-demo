use std::sync::Mutex;

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct SidecarState(Mutex<Option<CommandChild>>);

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let sidecar = app
                .shell()
                .sidecar("agent-demo-sidecar")?
                .args(["--host", "127.0.0.1", "--port", "18765"]);
            let (mut receiver, child) = sidecar.spawn()?;
            app.manage(SidecarState(Mutex::new(Some(child))));

            tauri::async_runtime::spawn(async move {
                while let Some(event) = receiver.recv().await {
                    println!("[agent-demo-sidecar] {:?}", event);
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                if let Some(state) = window.app_handle().try_state::<SidecarState>() {
                    if let Ok(mut child) = state.0.lock() {
                        if let Some(process) = child.take() {
                            let _ = process.kill();
                        }
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
