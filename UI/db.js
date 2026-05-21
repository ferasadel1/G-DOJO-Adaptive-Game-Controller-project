    const express = require('express');
    const cors = require('cors');
    const { Pool } = require('pg'); 

    const app = express();

    // Middleware to allow your HTML file to send data here
    app.use(cors());
    app.use(express.json());

    // 1. PostgreSQL Connection
    const pool = new Pool({
        user: 'postgres',
        host: 'localhost',
        database: 'UI', 
        password: '$Hulk5628', 
        port: 5432, 
    });

    pool.connect((err, client, release) => {
        if (err) {
            console.error('❌ Error connecting to the database:', err.stack);
        } else {
            console.log('✅ Successfully connected to local PostgreSQL database!');
        }
        if (client) release();
    });

    // 2. Automatically create the table if it doesn't exist
    async function initializeDB() {
        try {
            await pool.query(`
                CREATE TABLE IF NOT EXISTS player_profiles (
                    profile_name VARCHAR(100) PRIMARY KEY,
                    mapping_data JSONB NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            `);
            console.log("✅ Database table 'player_profiles' is ready!");
        } catch (err) {
            console.error("❌ Error creating table:", err.message);
        }
    }
    initializeDB();

    // 3. The API Endpoint that your HTML file calls when you click "SAVE"
    app.post('/api/save-regions', async (req, res) => {
        const { profile_name, regions } = req.body;

        if (!profile_name) {
            return res.status(400).json({ error: "Profile name is required." });
        }

        try {
            const query = `
                INSERT INTO player_profiles (profile_name, mapping_data, last_updated) 
                VALUES ($1, $2, CURRENT_TIMESTAMP) 
                ON CONFLICT (profile_name) 
                DO UPDATE SET 
                    mapping_data = EXCLUDED.mapping_data,
                    last_updated = CURRENT_TIMESTAMP
                RETURNING *;
            `;
            
            const values = [profile_name, JSON.stringify(regions)];
            const result = await pool.query(query, values);

            console.log(`💾 Saved profile to Database: ${profile_name}`);
            res.status(200).json({ success: true, data: result.rows[0] });

        } catch (err) {
            console.error("❌ Database update failed:", err.message);
            res.status(500).json({ error: "Failed to save to database." });
        }
    });

    // 4. The API Endpoint that your HTML file calls when you click the DELETE (Trash) icon
    app.post('/api/delete-profile', async (req, res) => {
        const { profile_name } = req.body;

        if (!profile_name) {
            return res.status(400).json({ error: "Profile name is required for deletion." });
        }

        try {
            const query = `DELETE FROM player_profiles WHERE profile_name = $1 RETURNING *;`;
            const result = await pool.query(query, [profile_name]);

            // Check if a row was actually deleted
            if (result.rowCount > 0) {
                console.log(`🗑️ Deleted profile from Database: ${profile_name}`);
                res.status(200).json({ success: true, message: "Profile deleted successfully." });
            } else {
                console.log(`⚠️ Profile not found in Database: ${profile_name}`);
                res.status(404).json({ error: "Profile not found in database." });
            }

        } catch (err) {
            console.error("❌ Database deletion failed:", err.message);
            res.status(500).json({ error: "Failed to delete from database." });
        }
    });

    // 5. Start the server
    const PORT = 3000;
    app.listen(PORT, () => {
        console.log(`🚀 Server is listening for the HTML file on http://localhost:${PORT}`);
    });