import os

import requests
import threading
from typing import Dict, List, Optional, Union

from .config import config
from .models.file import File
from .models.message import Message
from .models.terminal import Terminal
from .models.cursor import Cursor
from .models.api_key import APIKey
from .models.code_apply import CodeApplyChange


class ExtensionAPI:
    def __init__(self):
        self._local = threading.local()

    def load(self):
        self._local.uuid = os.environ['EXTENSION_UUID']
        host = os.environ['HOST']
        port = int(os.environ['PORT'])

        config.configure(host, port)

        kwargs = self._load_data()

        self._local.request_id = kwargs['request_id']
        self._local.repo_path = kwargs['repo_path']
        self._local.selection = kwargs.get('selection', None)
        self._local.clip_board = kwargs.get('clip_board', None)
        self._local.prompt = kwargs.get('prompt', None)
        self._local.chat_history = [Message(**m) for m in kwargs.get('chat_history', [])]
        self._local.current_terminal = kwargs.get('current_terminal', None)
        self._local.terminals = kwargs.get('terminals', [])
        self._local.api_keys = kwargs.get('api_keys', {})
        self._local.settings = kwargs.get('settings', {})
        self._local.ui_action = kwargs.get('ui_action', None)
        self._local.code_apply_change = kwargs.get('code_apply_change', None)

        opened_files = set(kwargs.get('opened_files'))
        self._local.repo_files = [File(p, self._local.repo_path, None, p in opened_files) for p in kwargs['repo']]

        if kwargs['current_file'] is not None:
            current_file_content = kwargs.get('current_file_content', None)
            self._local.current_file = File(kwargs['current_file'], self._local.repo_path, current_file_content, True)
        else:
            self._local.current_file = None

        context_files = {}
        for entry, values in kwargs.get('context_files', {}).items():
            files = [File(p, self._local.repo_path) for p in values]
            context_files[entry] = files
        self._local.context_files = context_files

        if kwargs['cursor'] is not None:
            self._local.cursor = Cursor(**kwargs['cursor'])
        else:
            self._local.cursor = None

    def cleanup(self):
        if hasattr(self._local, '__dict__'):
            self._local.__dict__.clear()

    def _dump(self, method: str, **kwargs):
        assert 'method' not in kwargs
        kwargs['method'] = method
        kwargs['request_id'] = self._local.request_id

        requests.post(f'http://{config.host}:{config.port}/api/extension/response/{self._local.uuid}', json=kwargs)

    def _load_data(self):
        response = requests.get(f'http://{config.host}:{config.port}/api/extension/data/{self._local.uuid}')
        response.raise_for_status()

        result = response.json()
        return result['data']

    def get_repo_files(self) -> List[File]:
        """
        Get all files in the repository.
        
        Returns:
            List[File]: A list of File objects representing all files in the repository.
        """
        return self._local.repo_files

    def get_repo_path(self) -> str:
        """
        Get the absolute path to the repository root.
        
        Returns:
            str: The repository root directory path.
        """
        return self._local.repo_path

    def get_current_file(self) -> Optional[File]:
        """
        Get the currently active file (current tab) in the editor.
        
        Returns:
            Optional[File]: The current File object, or None if no file is active.
        """
        return self._local.current_file

    def get_selection(self) -> Optional[str]:
        """
        Get the currently selected text in the editor.
        
        Returns:
            Optional[str]: The selected text, or None if no text is selected.
        """
        return self._local.selection

    def get_clip_board(self) -> Optional[str]:
        """
        Get the current clipboard contents.
        
        Returns:
            Optional[str]: The clipboard text, or None if empty.
        """
        return self._local.clip_board

    def get_cursor(self) -> Optional[Cursor]:
        """
        Get the current cursor position in the editor.
        
        Returns:
            Optional[Cursor]: The Cursor object with position information, or None.
        """
        return self._local.cursor

    def get_chat_history(self) -> List[Message]:
        """
        Get the chat conversation history.
        
        Returns:
            List[Message]: A list of Message objects representing the chat history.
        """
        return self._local.chat_history

    def get_current_terminal(self) -> Terminal:
        """
        Get the currently active terminal.
        
        Returns:
            Terminal: The current Terminal object.
        """
        return Terminal(self._local.current_terminal, True)

    def get_terminals(self) -> List[Terminal]:
        """
        Get all available terminals.
        
        Returns:
            List[Terminal]: A list of all Terminal objects, with the current one marked.
        """
        res = []
        for terminal in self._local.terminals:
            is_current_terminal = terminal == self._local.current_terminal
            res.append(Terminal(terminal, is_current_terminal))

        return res

    def get_code_apply_change(self) -> CodeApplyChange:
        """
        Get the current code change to be applied.
        
        Returns:
            CodeApplyChange: Object containing the patch information for code changes.
        """
        data = self._local.code_apply_change
        return CodeApplyChange(target_file_path=data['target_file_path'],
                               repo_path=self._local.repo_path,
                               patch_text=data['patch_text']
                               )

    def get_context_files(self) -> dict[str, list[File]]:
        """
        Get files that provide context for the current operation.
        
        Returns:
            dict[str, list[File]]: A dictionary mapping context entry names to lists of File objects.
        """
        return self._local.context_files

    def get_prompt(self) -> Optional[str]:
        """
        Get the user's prompt or query.
        
        Returns:
            Optional[str]: The user's prompt text entered in the chat input, or None if not provided.
        """
        return self._local.prompt

    def get_api_key(self, provider: str) -> Optional[APIKey]:
        """
        Get the API key for a specific provider.
        
        Args:
            provider: The name of the API provider (e.g., 'openrouter', 'deepinfra').
            
        Returns:
            Optional[APIKey]: The APIKey object for the provider, or None if not found.
        """
        if provider in self._local.api_keys:
            return APIKey(**self._local.api_keys[provider])

        return None

    def get_api_keys(self) -> List[APIKey]:
        """
        Get all configured API keys.
        
        Returns:
            List[APIKey]: A list of all APIKey objects.
        """
        res = []
        for k, v in self._local.api_keys.items():
            res.append(APIKey(**v))
        return res

    def get_setting(self, setting: str) -> Optional[any]:
        """
        Get a specific extension setting value.
        
        Args:
            setting: The name of the setting to retrieve.
            
        Returns:
            Optional[any]: The setting value, or None if not found.
        """
        return self._local.settings.get(setting, None)

    def get_ui_action(self) -> Dict[str, str]:
        """
        Get the current UI action being performed.
        
        Returns:
            Dict[str, str]: A dictionary containing UI action details.
        """
        return self._local.ui_action

    def chat(self, content: str):
        """
        Send a chat message to the IDE.
        
        Args:
            content: The message content to send.
        """
        self._dump('chat', content=content)

    def end_chat(self):
        """End the current chat session."""
        self._dump('end_chat')

    def start_chat(self):
        """Start a new chat session."""
        self._dump('start_chat')

    def autocomplete(self, suggestions: List[Dict[str, str]]):
        """
        Provide autocomplete suggestions to the IDE.
        
        Args:
            suggestions: A list of suggestion dictionaries containing completion options.
        """
        self._dump('autocomplete', suggestions=suggestions)

    def update_file(self, patch: List[str], matches: List[List[int]]):
        """
        Update a file with the provided patch.
        
        Args:
            patch: A list of patch lines to apply to the file.
            matches: A list of match positions for the patch application.
        """
        self._dump('update_file', patch=patch, matches=matches)

    def highlight(self, results: List[Dict[str, Union[int, str]]]):
        """
        Highlight specific code sections in the editor.
        
        Args:
            results: A list of highlight specifications with positions and styles.
        """
        self._dump('highlight', results=results)

    def inline_completion(self, text: str, cursor_row: int = None, cursor_column: int = None):
        """
        Provide inline code completion at the cursor position.
        
        Args:
            text: The completion text to insert.
            cursor_row: Optional row position for the completion.
            cursor_column: Optional column position for the completion.
        """
        self._dump('inline_completion', content=text, cursor_row=cursor_row, cursor_column=cursor_column)

    def log(self, message: str):
        """
        Log a message to the IDE console.
        
        Args:
            message: The message to log.
        """
        self._dump('log', content=message)

    def ui_form(self, title: str, form_content: str):
        """
        Display a custom HTML form in the IDE Tools UI.
        
        Args:
            title: The form title to display at the top of the form dialog.
            form_content: The HTML form content as a string. Should be a valid HTML form
                         with standard form elements like input, textarea, button, select, etc.
        """
        self._dump('ui_form', title=title, form_content=form_content)
