#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

// use tauri::command;
use screenshots::Screen; // Add screenshots crate
// use std::path::PathBuf;
use std::time::Instant;

#[tauri::command]
pub fn capture_screenshot() -> Result<String, String> {
    let screen = Screen::from_point(100, 100).map_err(|e| e.to_string())?;
    let image = screen.capture().map_err(|e| e.to_string())?;

    let path = std::env::temp_dir().join("screenshot.png");
    image.save(&path).map_err(|e| e.to_string())?;

    Ok(path.to_string_lossy().to_string())
}

pub fn screenshot() {
    let start = Instant::now();
    let screens = Screen::all().unwrap();

    for screen in screens {
        println!("capturer {screen:?}");
        let mut image = screen.capture().unwrap();
        image
            .save(format!("target/{}.png", screen.display_info.id))
            .unwrap();

        image = screen.capture_area(300, 300, 300, 300).unwrap();
        image
            .save(format!("target/{}-2.png", screen.display_info.id))
            .unwrap();
    }

    let screen = Screen::from_point(100, 100).unwrap();
    println!("capturer {screen:?}");

    let image = screen.capture_area(300, 300, 300, 300).unwrap();
    image.save("target/capture_display_with_point.png").unwrap();
    println!("运行耗时: {:?}", start.elapsed());
}