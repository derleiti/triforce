<?php
// Get the raw POST data
$json_data = file_get_contents('php://input');

// Decode the JSON data
$data = json_decode($json_data);

// Check if the data is valid
if ($data) {
    // Format the log entry
    $log_entry = 'CSP Violation: ' . print_r($data, true) . "\n";

    // Append the log entry to the script.log file
    file_put_contents('script.log', $log_entry, FILE_APPEND);
}
?>
