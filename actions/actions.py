"""
Actions personnalisées pour OUNIBOT - Chatbot ENSPD
Adapté du CollegeChatbot original
"""

from typing import Any, Text, Dict, List
import sqlite3
import os  # Ajouté pour os.path
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Chemin de la base de données - Utiliser le chemin absolu
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Database', 'ENSPD.db')
print(f"🔍 Chemin BD utilisé: {DB_PATH}")

# ===========================
#   FONCTIONS UTILITAIRES
# ===========================

def get_db_connection():
    """Établir une connexion à la base de données"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Erreur de connexion à la BD: {e}")
        return None

# ===========================
#   ACTIONS (classes seulement)
# ===========================

# ===========================
#   ACTION: INFORMATIONS FILIÈRE
# ===========================

class ActionInfoFiliere(Action):
    """Fournir des informations sur une filière de l'ENSPD"""
    
    def name(self) -> Text:
        return "action_info_filiere"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Récupérer l'entité filière
        filiere = next(tracker.get_latest_entity_values('filiere'), None)
        
        if not filiere:
            dispatcher.utter_message(text="De quelle filière voulez-vous des informations ? (GI, GC, GE, GMP, GT, GIND)")
            return []
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT code, nom, departement, duree_annees, description, 
                           nombre_places, chef_departement, frais_annuels
                    FROM filieres
                    WHERE LOWER(code) = LOWER(?) OR LOWER(nom) LIKE ?
                ''', (filiere, f'%{filiere.lower()}%'))
                
                row = cursor.fetchone()
                
                if row:
                    response = (
                        f"🎓 **{row['nom']} ({row['code']})**\n\n"
                        f"🏛️ **Département**: {row['departement']}\n"
                        f"⏱️ **Durée**: {row['duree_annees']} ans\n"
                        f"👥 **Places disponibles**: {row['nombre_places']}\n"
                        f"💰 **Frais annuels**: {row['frais_annuels']:,} FCFA\n"
                        f"👨‍🏫 **Chef de département**: {row['chef_departement']}\n\n"
                        f"📖 **Description**:\n{row['description']}\n\n"
                        f"Voulez-vous consulter le syllabus détaillé ?"
                    )
                    dispatcher.utter_message(text=response)
                    return [SlotSet("filiere", row['code'])]
                else:
                    dispatcher.utter_message(
                        text=f"Désolé, je n'ai pas trouvé d'informations sur '{filiere}'. "
                             f"Les filières disponibles sont: GI, GC, GE, GMP, GT, GIND."
                    )
                
                conn.close()
            except sqlite3.Error as e:
                dispatcher.utter_message(text=f"Erreur lors de la récupération des données: {e}")
        
        return []

# ===========================
#   ACTION: SYLLABUS
# ===========================

class ActionDemandeSyllabus(Action):
    """Fournir le lien vers le syllabus d'une filière"""
    
    def name(self) -> Text:
        return "action_demande_syllabus"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Récupérer la filière depuis le slot ou l'entité
        filiere = tracker.get_slot('filiere') or next(tracker.get_latest_entity_values('filiere'), None)
        
        if not filiere:
            dispatcher.utter_message(text="Pour quelle filière souhaitez-vous le syllabus ?")
            return []
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.url_syllabus, f.nom
                    FROM syllabus s
                    JOIN filieres f ON s.filiere_code = f.code
                    WHERE LOWER(s.filiere_code) = LOWER(?)
                ''', (filiere,))
                
                row = cursor.fetchone()
                
                if row:
                    response = (
                        f"📚 **Syllabus {row['nom']}**\n\n"
                        f"Vous pouvez consulter le syllabus détaillé via ce lien:\n"
                        f"🔗 {row['url_syllabus']}\n\n"
                        f"Le document contient:\n"
                        f"• Programme détaillé par semestre\n"
                        f"• Liste des matières et crédits\n"
                        f"• Objectifs pédagogiques\n"
                        f"• Modalités d'évaluation"
                    )
                    dispatcher.utter_message(text=response)
                else:
                    dispatcher.utter_message(
                        text=f"Le syllabus pour '{filiere}' n'est pas encore disponible. "
                             f"Contactez le service de scolarité pour plus d'informations."
                    )
                
                conn.close()
            except sqlite3.Error as e:
                dispatcher.utter_message(text=f"Erreur: {e}")
        
        return []

# ===========================
#   ACTION: INFORMATIONS GÉNÉRALES
# ===========================

class ActionInfoGenerale(Action):
    """Fournir des informations générales sur l'ENSPD"""
    
    def name(self) -> Text:
        return "action_info_generale"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Récupérer la catégorie demandée
        message = tracker.latest_message.get('text', '').lower()
        
        # Déterminer la catégorie
        if any(word in message for word in ['admission', 'intégrer', 'entrer', 'condition']):
            categorie = 'ADMISSION'
        elif any(word in message for word in ['concours', 'examen', 'épreuve']):
            categorie = 'CONCOURS'
        elif any(word in message for word in ['bourse', 'aide financière']):
            categorie = 'VIE_ESTUDIANTINE'
            titre = 'Bourses'
        elif any(word in message for word in ['logement', 'cité', 'résidence']):
            categorie = 'VIE_ESTUDIANTINE'
            titre = 'Logement'
        elif any(word in message for word in ['contact', 'adresse', 'téléphone']):
            categorie = 'GENERAL'
            titre = 'Contact'
        else:
            categorie = 'GENERAL'
            titre = 'Présentation ENSPD'
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Si titre spécifié
                if 'titre' in locals():
                    cursor.execute('''
                        SELECT contenu
                        FROM informations_enspd
                        WHERE categorie = ? AND titre = ?
                        LIMIT 1
                    ''', (categorie, titre))
                else:
                    cursor.execute('''
                        SELECT contenu
                        FROM informations_enspd
                        WHERE categorie = ?
                        LIMIT 1
                    ''', (categorie,))
                
                row = cursor.fetchone()
                
                if row:
                    dispatcher.utter_message(text=row['contenu'])
                else:
                    dispatcher.utter_message(response="utter_info_enspd")
                
                conn.close()
            except sqlite3.Error as e:
                dispatcher.utter_message(text=f"Erreur: {e}")
        
        return []

# ===========================
#   ACTION: CHANCES ADMISSION
# ===========================

class ActionChancesAdmission(Action):
    """Évaluer les chances d'admission selon le rang au concours"""
    
    def name(self) -> Text:
        return "action_chances_admission"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        rang = next(tracker.get_latest_entity_values('rang'), None)
        filiere = next(tracker.get_latest_entity_values('filiere'), None)
        
        if not rang:
            dispatcher.utter_message(text="Quel est votre rang au concours ?")
            return []
        
        try:
            rang_num = int(rang)
        except ValueError:
            dispatcher.utter_message(text="Veuillez indiquer un rang valide (nombre).")
            return []
        
        # Déterminer les chances selon le rang
        if rang_num <= 200:
            chances = "excellentes (95%)"
            conseil = "Félicitations ! Avec ce rang, vous avez d'excellentes chances d'être admis dans la filière de votre choix."
        elif rang_num <= 500:
            chances = "très bonnes (80%)"
            conseil = "Très bon rang ! Vous avez de fortes chances d'admission, surtout si vous privilégiez les filières GC, GE ou GMP."
        elif rang_num <= 1000:
            chances = "moyennes (50%)"
            conseil = "Chances correctes. Privilégiez les filières GC, GE, GMP ou GIND pour maximiser vos chances."
        elif rang_num <= 1500:
            chances = "limitées (30%)"
            conseil = "Les chances sont plus faibles. Je vous recommande de cibler GMP, GIND ou GC. Préparez également un plan B."
        else:
            chances = "faibles (15%)"
            conseil = "Les chances d'admission sont limitées avec ce rang. Envisagez de repasser le concours l'année prochaine ou de postuler dans d'autres établissements."
        
        response = (
            f"🎯 **Évaluation pour le rang {rang_num}**\n\n"
            f"📊 Chances d'admission: **{chances}**\n\n"
        )
        
        if filiere:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT nom FROM filieres WHERE LOWER(code) = LOWER(?)", (filiere,))
                row = cursor.fetchone()
                if row:
                    response += f"📚 Filière visée: {row['nom']}\n\n"
                conn.close()
        
        response += f"💡 **Conseil**: {conseil}\n\n"
        response += "Pour plus d'informations, consultez les statistiques détaillées sur notre site web."
        
        dispatcher.utter_message(text=response)
        return []

# ===========================
#   ACTION: LISTE FILIÈRES
# ===========================

class ActionListeFilieres(Action):
    """Lister toutes les filières disponibles"""
    
    def name(self) -> Text:
        return "action_liste_filieres"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT code, nom, nombre_places
                    FROM filieres
                    ORDER BY code
                ''')
                
                filieres = cursor.fetchall()
                
                if filieres:
                    response = "🎓 **Filières de l'ENSPD**\n\n"
                    
                    for i, fil in enumerate(filieres, 1):
                        response += f"{i}️⃣ **{fil['nom']} ({fil['code']})**\n"
                        response += f"   📊 Places: {fil['nombre_places']}\n\n"
                    
                    response += "\nPour plus d'informations sur une filière, demandez: 'Parle-moi de GI'"
                    
                    dispatcher.utter_message(text=response)
                else:
                    dispatcher.utter_message(text="Aucune filière trouvée.")
                
                conn.close()
            except sqlite3.Error as e:
                dispatcher.utter_message(text=f"Erreur: {e}")
        
        return []

# ===========================
#   ACTION: FALLBACK
# ===========================

class ActionDefaultFallback(Action):
    """Action de fallback par défaut"""
    
    def name(self) -> Text:
        return "action_default_fallback"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(
            text="Désolé, je n'ai pas bien compris votre demande. 😕\n\n"
                 "Je peux vous aider avec:\n"
                 "• Informations sur les filières\n"
                 "• Conditions d'admission\n"
                 "• Concours d'entrée\n"
                 "• Bourses et logement\n"
                 "• Contact de l'école\n\n"
                 "Tapez 'aide' pour voir toutes mes fonctionnalités."
        )
        return []

# ===========================
#   ANCIENNES ACTIONS (Compatibilité)
# ===========================

class ActionHelloWorld(Action):
    """Action simple de test"""
    
    def name(self) -> Text:
        return "action_hello_world"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World from OUNIBOT!")
        return []

class ActionSpecifyProgram(Action):
    """Demander la filière (ancienne version)"""

    def name(self) -> Text:
        return "action_which_program"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="De quelle filière voulez-vous des informations ?")
        return []