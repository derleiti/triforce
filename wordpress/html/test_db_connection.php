<?php
// Load WordPress for database credentials
require_once('wp-load.php');

$servername = DB_HOST;
$username = DB_USER;
$password = DB_PASSWORD;
$dbname = DB_NAME;

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname);

// Check connection
if ($conn->connect_error) {
    echo "Connection failed: " . $conn->connect_error; // Changed to echo for direct output
    exit(); // Exit after printing error
}
echo "Connected successfully";
$conn->close();
?>